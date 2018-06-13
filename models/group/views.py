import os
import traceback
import uuid
import shortid
import werkzeug
from flask import Blueprint, request, render_template, session, url_for, flash
from werkzeug.utils import secure_filename, redirect
import models.users.decorators as user_decorators
from models.error_logs.error_log import Error_
from models.group.group import Group
from models.messages.message import Message
from models.notes.note import Note
from models.users.user import User
from models.group.constants import ALLOWED_GROUP_IMG_FORMATS

group_blueprint = Blueprint('groups', __name__)
#
#
# def share_bool_function(share):
#     if share == '0':
#         share = False
#     elif share == '1':
#         share = True
#     elif share == '2':
#         share = True
#
#     return share


@group_blueprint.route('/group/_join/_joingroup_/<string:list_>')
@user_decorators.require_login
def join_group_(list_):
    list__ = list_.split(',')
    # saving group with user id

    group_ = Group.find_by_id(list__[1])

    if session['_id'] in group_.members:
        flash('You\'ve already joined this group!')
    else:

        group_.members.extend([session['_id']])
        group_.save_to_elastic()
        group_.save_to_mongo()

    # saving to user database
    user_ = User.find_by_id(session['_id'])
    user_.group_id = group_._id
    user_.save_to_mongo()

    # if invatation, then remove the message and flash a message
    message = Message.find_by_id(list__[0])
    message.delete_on_elastic()
    message.delete()

    flash('Your invitation has expired.')

    # redirecting
    flash('Joined group successfully')

    return redirect(url_for('.group', group_id=list__[1]))


@group_blueprint.route('/group/_join/_joingroup/<string:group_id>')
@user_decorators.require_login
def join_group(group_id):
    # saving group with user id
    group_ = Group.find_by_id(group_id)
    group_.members.extend([session['_id']])
    group_.save_to_elastic()
    group_.save_to_mongo()

    # saving to user database
    user_ = User.find_by_id(session['_id'])
    user_.group_id = group_._id
    user_.save_to_mongo()

    # redirecting
    flash('Joined group successfully')
    return redirect(url_for('.group', group_id=group_id))


@group_blueprint.route('/group/<string:group_id>')
@user_decorators.require_login
def group(group_id):
    try:
        group_ = Group.find_by_id(group_id)
        members = []
        shared_notes = []
        for member in group_.members:
            members.append(User.find_by_id(member))

        for note in group_.shared_notes:
            shared_notes.append(Note.find_by_id(note['note_id']))

        if session['_id'] in group_.members:
            is_in_group = True
        else:
            is_in_group = False

        return render_template('groups/group.html', group=group_, members=members, shared_notes=shared_notes,
                               is_in_group=is_in_group, session_id=session['_id'])
    except:
        error_msg = traceback.format_exc().split('\n')

        Error_obj = Error_(error_msg=''.join(error_msg), error_location='group getting group')
        Error_obj.save_to_mongo()
        return render_template('error_page.html', error_msgr='Crashed during getting your group info...')


@group_blueprint.route('/groups', methods=['GET', 'POST'])
@user_decorators.require_login
def groups():
    try:
        all_groups = Group.get_all_shared_groups()

        if request.method == 'POST':
            form = request.form['Search']
            all_groups = Group.search_with_elastic(form_data=form, shared=True)

            return render_template('groups/shared_groups.html', all_groups=all_groups, form=form)
        return render_template('groups/shared_groups.html', all_groups=all_groups)
    except:
        error_msg = traceback.format_exc().split('\n')

        Error_obj = Error_(error_msg=''.join(error_msg), error_location='groups shared_groups')
        Error_obj.save_to_mongo()
        return render_template('error_page.html', error_msgr='Crashed during getting groups...')


def gen_all_friends_diclist():
    all_firends_ = User.find_by_id(session['_id']).get_friends()
    all_firends_diclist = []
    for user in all_firends_:
        try:
            image = url_for('static', filename=user.picture)
        except werkzeug.routing.BuildError:
            image = url_for('static', filename='img/index.jpg')

        all_firends_diclist.append({'url': image, 'user_id': user._id,
                                    "last_logined": user.last_logined,
                                    "nickname": user.nick_name,
                                    "email": user.email})

    return all_firends_diclist


@group_blueprint.route('/create_group', methods=['GET', 'POST'])
@user_decorators.require_login
def create_group():
    try:
        if request.method == 'GET':

            all_firends_diclist = gen_all_friends_diclist()

            return render_template('groups/create_group.html', all_firends=all_firends_diclist)

        if request.method == 'POST':
            user = User.find_by_id(session['_id'])

            name = request.form['name']
            members = request.form.getlist('members')
            members.append(user._id)

            try:
                group_img = request.form['img']
            except:
                group_img = None

            description = request.form['description']
            share = request.form['inputGroupSelect01']
            if group_img is not None:
                file_name, file_extenstion = os.path.splitext(group_img)
                if file_extenstion not in ALLOWED_GROUP_IMG_FORMATS or len(group_img) > 1:
                    all_firends_diclist = gen_all_friends_diclist()
                    return render_template('groups/create_group.html',
                                           all_firends=all_firends_diclist
                                           , error_msg='Too much images!! Please upload just one image.',
                                           name=name, members=members, share=share, description=description)

                # saving file
                # create name for file
                sid = shortid.ShortId()
                # create path for file
                file_path, file_extenstion = os.path.splitext(group_img.filename)
                filename = secure_filename(sid.generate()) + file_extenstion

                # os.chdir("static/img/file/")
                # save file and add file to filenames list
                group_img.save(os.path.join(filename))
            else:
                filename = None

            # saving group
            group_id = uuid.uuid4().hex

            group_for_save = Group(_id=group_id, name=name, members=[user._id],
                                   group_img_name=filename, shared=share, shared_notes=[], description=description)
            group_for_save.save_to_mongo()
            group_for_save.save_to_elastic()

            # # saving to user
            user.group_id = group_id
            user.save_to_mongo()

            # sending messages to users

            for member in members:
                message = Message(title='Do you want to join my group?', content='''
                    Join me on group {}!
                    If you want to join, please click the link below.
                '''.format(group_for_save.name), is_invtation=group_id, reciver_id=member, sender_id=user._id)
                message.save_to_elastic()
                message.save_to_mongo()

            # redirecting
            flash('Successfully saved to database!')
            flash('Sended invitations to users')
            return redirect(url_for('groups.groups'))


    except:
        error_msg = traceback.format_exc().split('\n')

        Error_obj = Error_(error_msg=''.join(error_msg), error_location='create_group creating group')
        Error_obj.save_to_mongo()
        return render_template('error_page.html', error_msgr='Crashed during creating your group...')


@group_blueprint.route('/my_group')
@user_decorators.require_login
def my_group():
    current_user = User.find_by_id(session['_id'])
    user_group_id = current_user.group_id
    if user_group_id is None:
        return render_template('groups/my_group_demo.html')
    else:

        return redirect(url_for('groups.group', group_id=user_group_id))


@group_blueprint.route('/get_out_group/<string:group_id>')
@user_decorators.require_login
def get_out_group(group_id):
    # save to user object
    user = User.find_by_id(session['_id'])
    user.group_id = None
    user.save_to_mongo()
    # save to group object
    group_ = Group.find_by_id(group_id)
    group_.members.remove(user._id)
    group_notes = group_.shared_notes
    # group_.shared_notes.remove({'author': user._id})
    # integrating through group notes and deleting notes from group
    for note in group_notes:
        # saving changes to note
        note_ = Note.find_by_id(note['note_id'])
        note_.share_with_group = False
        note_.save_to_mongo()
        note_.save_to_elastic()

        # removing note from group
        group_notes.remove({'author': user._id, 'note_id': note['note_id']})

    if not group_.members:
        group_.delete_on_elastic()
        group_.delete_img()
        group_.delete()
        flash('The group you secessioned was deleted because it has no members.')
    else:
        group_.save_to_mongo()
        group_.update_to_elastic()
        flash('Secession complete')

    return redirect(url_for('groups.groups'))


@group_blueprint.route('/invite/invite_friend/', methods=['GET', 'POST'])
@user_decorators.require_login
def invite_friend():
    user_ = User.find_by_id(session['_id'])
    all_friends = gen_all_friends_diclist()
    group_ = Group.find_by_id(user_.group_id)
    group_name = group_.name
    group_members = group_.members

    for friend in all_friends:

        for group_member in group_members:
            try:
                if group_member == friend['user_id']:
                    all_friends.remove(friend)
            except UnboundLocalError:
                break

    if request.method == 'POST':
        users = request.form.getlist('users')
        group_.members.extend(users)
        group_.save_to_mongo()
        group_.save_to_elastic()

        return redirect(url_for('groups.group', group_id=group_._id))

    return render_template('groups/invite_friend.html', friends=all_friends, group_name=group_name)

