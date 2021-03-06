import datetime
import uuid
import shortid
from common.database import Database
from models.chatboxs.constants import COLLECTION as ChatBoxConstants
from models.messages.message import Message
from models.users.user import User


class ChatBox(object):

    def __init__(self, _id=None, user_ids=[], messages=[], created_date=datetime.datetime.now(), name=None, last_logined=None):
        self._id = uuid.uuid4().hex if _id is None else _id
        self.user_ids = user_ids
        self.messages = messages
        self.created_date = created_date
        self.last_logined = last_logined
        id_gen_sid = shortid.ShortId()
        self.name = id_gen_sid.generate() if name is '' else name

    def json(self):
        return {
            "_id": self._id,
            "user_ids": self.user_ids,
            "messages": self.messages,
            "created_date": self.created_date,
            "last_logined": self.last_logined,
            "name": self.name
        }

    def save_to_mongo(self):
        Database.update(ChatBoxConstants, {"_id": self._id}, self.json())

    @classmethod
    def find_by_id(cls, chatbox_id):
        try:
            return cls(**Database.find_one(ChatBoxConstants, {'_id': chatbox_id}))
        except TypeError:
            return None

    def limit_find_messages(self):
        try:
            messages = []

            if len(self.messages) < 20:
                for message in self.messages:
                    message_obj = Message.find_by_id_chat(message)
                    if message_obj is not None:
                        messages.append(message_obj)
                return messages
            else:
                for message in self.messages[20:]:
                    message_obj = Message.find_by_id_chat(message)
                    if message_obj is not None:
                        messages.append(message_obj)
                return messages

        except TypeError:
            return None

    @classmethod
    def get_user_chatboxs(cls, user_id):
            return [cls(**elem) for elem in Database.find(ChatBoxConstants,  {'user_ids': {"$in": [user_id]}})]

    @classmethod
    def latest_message_(cls):
        try:
            return cls(**Database.get_latest_data(ChatBoxConstants, {}))
        except TypeError:
            return None

    def delete_member(self, member_id):
        # returns false when error accorded
        try:
            self.user_ids.remove(member_id)
        except ValueError:
            return False

    def add_member(self, user_id):
        # addes member by extending list
        self.user_ids.extend([user_id])

    def delete_message(self, message_id):
        """

        :param message_id: message's _id
        :return: returns false when error accorded
        """
        try:
            self.messages.remove(message_id)
        except ValueError:
            return False

    def add_message(self, message_id):
        self.messages.extend([message_id])

    def get_members(self):
        members = []
        for user in self.user_ids:
            members.append(User.find_by_id(user))

        return members
    #
    # def get_user_chatboxs(self):
    #     try:
    #         return [cls(**elem) for elem in Database.find(ChatBoxConstants,
    #                                                   {'reciver_id': })]
    #     except TypeError:
    #         return None
