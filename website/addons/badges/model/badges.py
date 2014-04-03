import calendar
from bson import ObjectId
from datetime import datetime

from framework import fields
from framework import GuidStoredObject, StoredObject

from website.settings import DOMAIN

from website.addons.badges.util import deal_with_image


class Badge(GuidStoredObject):

    redirect_mode = 'proxy'

    _id = fields.StringField(primary=True)

    creator = fields.ForeignField('badgesusersettings', backref='creator')

    is_system_badge = fields.BooleanField(default=False)

    #Open Badge protocol
    name = fields.StringField()
    description = fields.StringField()
    image = fields.StringField()
    criteria = fields.StringField()
    #TODO
    alignment = fields.DictionaryField(list=True)
    tags = fields.StringField(list=True)

    @classmethod
    def create(cls, user_settings, badge_data, save=True):
        badge = cls()
        badge.creator = user_settings
        badge.name = badge_data['badgeName']
        badge.description = badge_data['description']
        badge.criteria = badge_data['criteria']
        badge._ensure_guid()
        badge.image = deal_with_image(badge_data['imageurl'], badge._id)
        if save:
            badge.save()
        return badge

    def make_system_badge(self, save=True):
        self.is_system_badge = True
        self.save()

    def to_json(self):
        return {
            'id': self._id,
            'name': self.name,
            'description': self.description,
            'image': self.image,
            'criteria': self.criteria,
            'alignment': self.alignment,
            'tags': self.tags,
        }

    def to_openbadge(self):
        return {
            'name': self.name,
            'description': self.description,
            'image': self.image,
            'criteria': self.criteria,
            'issuer': '{0}badge/organization/{1}/json/'.format(DOMAIN, self.creator.owner._id),
            'url': '{0}{1}/json/'.format(DOMAIN, self._id),
            'alignment': self.alignment,
            'tags': self.tags,
        }

    @property
    def description_short(self):
        words = self.description.split(' ')
        if len(words) < 9:
            return ' '.join(words)
        return '{}...'.format(' '.join(words[:9]))

    #TODO Auto link urls?
    @property
    def criteria_list(self):
        tpl = '<ul>{}</ul>'
        stpl = '<li>{}</li>'
        lines = self.criteria.split('\n')
        return tpl.format(' '.join([stpl.format(line) for line in lines if line]))  # Please dont kill me Steve

    @property
    def assertions(self):
        return self.badgeassertion__assertion

    @property
    def awarded(self):
        return len(self.assertions)

    @property
    def unique_awards(self):
        return len({assertion.node._id for assertion in self.assertions})

    @property
    def deep_url(self):
        return '/badge/{}/'.format(self._id)

    @property
    def url(self):
        return '/badge/{}/'.format(self._id)


#TODO verification hosted and signed
class BadgeAssertion(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))

    #Backrefs
    badge = fields.ForeignField('badge', backref='assertion')
    node = fields.ForeignField('node', backref='awarded')
    _awarder = fields.ForeignField('badgesusersettings', backref='awarder')

    #Custom fields
    revoked = fields.BooleanField(default=False)
    reason = fields.StringField()

    #Required
    issued_on = fields.IntegerField(required=True)

    #Optional
    evidence = fields.StringField()
    expires = fields.StringField()

    @classmethod
    def create(cls, badge, node, evidence=None, save=True, awarder=None):
        b = cls()
        b.badge = badge
        b.node = node
        b.evidence = evidence
        b.issued_on = calendar.timegm(datetime.utctimetuple(datetime.utcnow()))
        b._awarder = awarder
        if save:
            b.save()
        return b

    def to_json(self):
        return {
            'uid': self._id,
            'recipient': self.node._id,
            'badge': self.badge._id,
            'verify': self.verify,
            'issued_on': self.issued_date,
            'evidence': self.evidence,
            'expires': self.expires
        }

    def to_openbadge(self):
        return {
            'uid': self._id,
            'recipient': self.recipient,
            'badge': '{}{}/json/'.format(DOMAIN, self.badge._id),
            'verify': self.verify,
            'issuedOn': self.issued_on,
            'evidence': self.evidence,
            'expires': self.expires
        }

    @property
    def issued_date(self):
        return datetime.fromtimestamp(self.issued_on).strftime('%Y/%m/%d')

    @property
    def verify(self, vtype='hosted'):
        return {
            'type': 'hosted',
            'url': '{}badge/assertion/json/{}/'.format(DOMAIN, self._id)
        }

    @property
    def recipient(self):
        return {
            'idenity': self.node._id,
            'type': 'osfnode',  # TODO Could be an email?
            'hashed': False
        }

    @property
    def awarder(self):
        if self.badge.is_system_badge and self._awarder:
            return self._awarder
        return self.badge.creator
