import datetime
from models.error_logs.error_log import Error_
from flask import Blueprint, request, session, url_for, render_template, flash
from werkzeug.utils import redirect
from models.messages.message import Message
import models.users.decorators as user_decorators
from models.notes.note import Note
from models.users.user import User
import traceback
from flask import make_response

message_blueprint = Blueprint('message', __name__)


def label_maker(messages, user_id):
    labels = []
    for message in messages:
        try:
            if message.sender_id == user_id:
                labels.append({"message_id": message._id, "label": "sended"})
            elif user_id in message.reciver_id:
                labels.append({"message_id": message._id, "label": "recived"})
        except:
            pass
        # else:
        #     raise Exception(message.sender_id + ' ' + user_id + ' ' + str(message.reciver_id))

    return labels
#
#
# @message_blueprint.route('/set_cookie/set/<is_invtation>')
# def cookie_maker(is_invtation):
#     resp = make_response()
#     resp.set_cookie('is_invtation', is_invtation)
#     return resp


@message_blueprint.route('/all_messages/<string:user_id>', methods=['GET', 'POST'])
@user_decorators.require_login
def all_messages(user_id):
    try:
        user_nickname = User.find_by_id(session['_id']).nick_name

        if request.method == 'POST':
            form_ = request.form['Search_message']

            messages = Message.search_find_all(form_, user_id)

            labels = label_maker(messages, user_id)

            return render_template('messages/messages.html',
                                   messages=messages, user_nickname=user_nickname, form=form_, labels=labels)
        messages = Message.search_find_all('', user_id)
        labels = label_maker(messages, user_id)
        if messages is None or None in messages:
            messages = []
            labels = []

        return render_template('messages/messages.html',
                               messages=messages, user_nickname=user_nickname, labels=labels)

    except:
        error_msg = traceback.format_exc().split('\n')

        Error_obj = Error_(error_msg=''.join(error_msg), error_location='my_recived_messages-during message finding')
        Error_obj.save_to_mongo()
        return render_template('base_htmls/error_page.html', error_msgr='Crashed during reading your messages')


@message_blueprint.route('/recived_messages/<string:user_id>', methods=['GET', 'POST'])
@user_decorators.require_login
def my_recived_messages(user_id):
    try:
        messages_by_db = Message.find_by_reciver_id(user_id)
        user_nickname = User.find_by_id(session['_id']).nick_name

        if request.method == 'POST':
            form_ = request.form['Search_message']

            messages = Message.search_on_elastic(form_, user_id)

            try:
                for message in messages:
                    if type(message) is 'NoneType':
                        messages.remove(message)
            except TypeError:
                pass

            if messages is None:
                messages = []

            return render_template('messages/my_recived_messages.html',
                                   messages=messages, user_nickname=user_nickname, form=form_)
        return render_template('messages/my_recived_messages.html',
                               messages=messages_by_db, user_nickname=user_nickname)

    except:
        error_msg = traceback.format_exc().split('\n')

        Error_obj = Error_(error_msg=''.join(error_msg), error_location='my_recived_messages-during message finding')
        Error_obj.save_to_mongo()
        return render_template('base_htmls/error_page.html', error_msgr='Crashed during reading your messages')


@message_blueprint.route('/sended_messages/<string:user_id>')
@user_decorators.require_login
def my_sended_messages(user_id):
    try:
        messages = Message.find_by_sender_id(user_id)
        user_nickname = User.find_by_id(session['_id']).nick_name

        return render_template('messages/my_sended_messages.html', messages=messages, user_nickname=user_nickname)

    except:
        error_msg = traceback.format_exc().split('\n')

        Error_obj = Error_(error_msg=''.join(error_msg), error_location='my_sended_messages-during message finding')
        Error_obj.save_to_mongo()
        return render_template('base_htmls/error_page.html', error_msgr='Crashed during reading your messages')


@message_blueprint.route('/send_message', methods=['GET', 'POST'])
@user_decorators.require_login
def send_message(user_to_send=None):

    try:
        all_users = User.get_all()

        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']

            if request.form.getlist("user") in [None, [], ""]:
                return render_template('messages/send_message.html',
                                       e="You hadn't selected an reciver. Please select at least ONE reciver.",
                                       all_users=all_users, title=title, content=content)

            else:

                recivers = request.form.getlist("user")
            sender = User.find_by_email(session['email'])
            sender_name = sender.nick_name
            sender_id = sender._id

            message = Message(title=title, content=content,
                              reciver_id=recivers, sender_id=sender_id, is_a_noteOBJ=False, sender_name=sender_name,
                              is_chat_message=False)
            message.save_to_mongo()
            message.save_to_elastic()

            return redirect(url_for('.my_sended_messages', user_id=sender_id))

        if user_to_send is not None:
            return render_template('messages/send_message.html', all_users=all_users, user_to_send=user_to_send)
        else:
            return render_template('messages/send_message.html', all_users=all_users)

    except:
        error_msg = traceback.format_exc().split('\n')

        Error_obj = Error_(error_msg=''.join(error_msg), error_location='send_message message sending')
        Error_obj.save_to_mongo()
        return render_template('base_htmls/error_page.html', error_msgr='Crashed during sending your message...')


@message_blueprint.route('/message/<string:message_id>')
@user_decorators.require_login
def message(message_id, is_sended=False):

    try:

        message = Message.find_by_id(message_id)

        if message is None:
            pass

        if message.readed_by_reciver is False and is_sended is False and session['_id'] in message.reciver_id and message.readed_date is None:
            message.readed_by_reciver = True
            message.readed_date = datetime.datetime.now()
            message.save_to_mongo()
            message.update_to_elastic()

        sender_nickname = User.find_by_id(message.sender_id).nick_name
        if type(message.reciver_id) is list:
            reciver_nickname = []
            for reciver in message.reciver_id:
                reciver_nickname.append(User.find_by_id(reciver).nick_name)

        else:
            reciver_nickname = User.find_by_id(message.reciver_id).nick_name

        if message.is_a_noteOBJ:
            try:
                note = Note.find_by_id(message.content)
            except:
                note = None
        else:
            note = None
        resp = make_response(render_template('messages/message.html', message=message, sender_nickname=sender_nickname,
                               reciver_nickname=reciver_nickname, is_a_note=message.is_a_noteOBJ, note=note,
                                             join_group_redirect_info=','.join([message_id, message.is_invtation])))

        return resp

    except:
        error_msg = traceback.format_exc().split('\n')

        Error_obj = Error_(error_msg=''.join(error_msg), error_location='message message reading')
        Error_obj.save_to_mongo()

        return render_template('base_htmls/error_page.html', error_msgr='Crashed during reading message...')


@message_blueprint.route('/delete_message/<string:message_id>')
@user_decorators.require_login
def delete_message(message_id):
    try:
        message = Message.find_by_id(message_id)
        message.delete_on_elastic()
        message.delete()

        # flash('Your message has successfully deleted.')
        flash('{ "message":"Your message has successfully deleted.", "type":"success" , "captaion":"Delete Success", "icon_id": "far fa-check-circle"}')

        return redirect(url_for('.my_recived_messages', user_id=session['_id']))

    except:
        error_msg = traceback.format_exc().split('\n')

        Error_obj = Error_(error_msg=''.join(error_msg), error_location='delete_message message deleting')
        Error_obj.save_to_mongo()
        return render_template('base_htmls/error_page.html', error_msgr='Crashed during deleteing your message...')


@message_blueprint.route('/send_note', methods=['GET', 'POST'])
@user_decorators.require_login
def send_note():
    try:
        all_notes = Note.get_all()
        all_users = User.get_all()

        if request.method == 'POST':

            try:
                note = Note.find_by_id(request.form['note'])
            except:

                error_msg = traceback.format_exc().split('\n')

                Error_obj = Error_(error_msg=''.join(error_msg), error_location='send_note note finding/reading')
                Error_obj.save_to_mongo()

                return render_template('base_htmls/error_page.html', error_msgr='Crashed during preparing page...')

            message_title = request.form['title']

            if request.form.getlist("user") in [None, [], ""]:
                return render_template('messages/send_note.html',
                                       e="You hadn't selected an reciver. Please select at least ONE reciver.",
                                       all_users=all_users, title=message_title,)

            else:

                recivers = request.form.getlist("user")

            sender = User.find_by_email(session['email'])
            sender_name = sender.nick_name
            sender_id = sender._id

            message = Message(title=message_title, content=note._id, reciver_id=recivers, sender_id=sender_id, is_a_noteOBJ=True,
                              sender_name=sender_name)
            message.save_to_mongo()
            message.save_to_elastic()

            # flash('Your message has been successfully sended.')
            flash('{ "message":"Your message has been successfully sended.", "type":"success" , "captaion":"Send Success", "icon_id": "far fa-check-circle"}')

            return redirect(url_for('.my_sended_messages', user_id=sender_id))

        return render_template('messages/send_note.html',
                               all_notes=all_notes, all_users=all_users)

    except:
        error_msg = traceback.format_exc().split('\n')

        Error_obj = Error_(error_msg=''.join(error_msg), error_location='message message sending')
        Error_obj.save_to_mongo()

        return render_template('base_htmls/error_page.html', error_msgr='Crashed during sending message...')


@message_blueprint.route('/send_note_<string:note_id>', methods=['GET', 'POST'])
@user_decorators.require_login
def send_note_radio(note_id):
    try:
        note = Note.find_by_id(note_id)
        all_notes = Note.get_all()
        all_users = User.get_all()

        if request.method == 'POST':

            try:
                note = Note.find_by_id(request.form['note'])
            except:

                error_msg = traceback.format_exc().split('\n')

                Error_obj = Error_(error_msg=''.join(error_msg), error_location='send_note note finding/reading')
                Error_obj.save_to_mongo()

                return render_template('base_htmls/error_page.html', error_msgr='Crashed during preparing page...')

            message_title = request.form['title']

            if request.form.getlist("user") in [None, [], ""]:
                return render_template('messages/send_note.html',
                                       e="You hadn't selected an reciver. Please select at least ONE reciver.",
                                       all_users=all_users, title=message_title,)

            else:

                recivers = request.form.getlist("user")

            sender_id = User.find_by_email(session['email'])._id

            message = Message(title=message_title, content=note._id, reciver_id=recivers, sender_id=sender_id, is_a_noteOBJ=True)
            message.save_to_mongo()
            message.save_to_elastic()

            # flash('Your message has been successfully sended.')
            flash('{ "message":"Your message has been successfully sended.", "type":"success" , "captaion":"Send Success", "icon_id": "far fa-check-circle"}')

            return redirect(url_for('.my_sended_messages', user_id=sender_id))

        return render_template('messages/send_note.html',
                               all_notes=all_notes, all_users=all_users, note_=note)

    except:
        error_msg = traceback.format_exc().split('\n')

        Error_obj = Error_(error_msg=''.join(error_msg), error_location='message message sending')
        Error_obj.save_to_mongo()

        return render_template('base_htmls/error_page.html', error_msgr='Crashed during sending message...')


@message_blueprint.route('/choose/')
@user_decorators.require_login
def choose():
    return render_template('messages/choose_message_type.html')
