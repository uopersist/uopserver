import uop.db_interface as db_iface
from uop.biz import services, user


class ServerInterface:
    def __init__(self, db, standard_app=None, user_id=None):
        self._standard_app = standard_app
        self._user_id = user_id
        self.service = services.Services(db)
        self._iface = db_iface.Interface(db, user_id=user)
        self._by_name = dict()

    def set_user(self, user_id):
        self._user_id = user_id

    def _kind_instances(self, kind):
        return self.get_metadata()[kind].values()

    def _kind_by_name(self, kind):
        by_name = self._by_name.get(kind)
        if not by_name:
            by_name = dict([(x.name, x) for x in self._kind_instances(kind)])
            self._by_name[kind] = by_name
        return by_name

    def _get_named(self, kind, a_name):
        return self._kind_by_name(kind).get(a_name)

    def get_metadata(self):
        pass

    def get_by_id(self, kind, anId):
        return self.get_metadata()[kind][anId]

    def get_by_name(self, kind, name):
        return self._kind_by_name(kind).get(name)

    def insert(self, kind, data):
        pass

    def modify(self, kind, anId, mods):
        pass

    def delete(self, kind, anId):
        pass

    def login(self, username, password):
        user = self.service.login_user(username, password)
        self._iface = db_iface.Interface(self._db, user_id=user['_id'])
        return user

    def register(self, username, password, email):
        return self.service.register_user(username, password, email)

    def __getattr__(self, name):
        return getattr(self._iface, name)
