from telebot import types
from . import fields
from . import tb_fsm as ffsm
from .validators import all_content_types
from . import validators
from .tb_fsm import TB_FORM_TAG,DEFAULT_CANCEl_CALLBACK,FIELD_CLICK_CALLBACK_DATA_PATTERN,FSM_FORM_IDE,DEFAULT_SUBMIT_CALLBACK,FSM_GET_FIELD_VALUE,DEFAULT_CANCEl_FORM_CALLBACK,DEFAULT_VALUE_FROM_CALLBACK_PATTERN
from collections import namedtuple
import pickle
import types as build_in_types

__version__ = "0.9.5"

class EventCollector:
    _submit_collector = {}
    _cancel_collector = {}
    _global_cancel = None
    _global_submit = None

    def register_submit(self,name,func):
        self._submit_collector[name] = func

    def register_cancel(self,name,func):
        self._cancel_collector[name] = func


    def get_submit(self,name):
        if name in list(self._submit_collector.keys()):
            return self._submit_collector[name]
        return False

    def get_cancel(self,name):
        if name in list(self._cancel_collector.keys()):
            return self._cancel_collector[name]
        return False


class FormEvent:
    def __init__(self,event_type: str,sub_event_type = None,event_data = None):
        self.event_type = event_type
        self.sub_event_type = sub_event_type
        self.event_data = event_data

    def __repr__(self):
        return "<FormEvent(event_type='{}',sub_event_type='{}',event_data={})>".format(self.event_type,self.sub_event_type,self.event_data)



class TelebotForms:
    """ Основной класс дополнения """
    GLOBAL_MISSING_VALUE_ICON = None
    GLOBAL_READ_ONLY_ICON = None
    GLOBAL_EDIT_ICON = None
    GLOBAL_CANCEL_BUTTON_TEXT = None
    GLOBAL_CANCEL_CALLBACK = None
    GLOBAL_CANCELED_TEXT = None
    GLOBAL_SUBMIT_BUTTON_TEXT = None
    GLOBAL_CLOSE_FORM_BUT = None
    GLOBAL_FREEZE_MODE = None
    GLOBAL_STOP_FREEZE_TEXT = None
    GLOBAL_LIFE_TIME = None
    GLOBAL_INVALID_INPUT_TEXT = None


    def __init__(self,bot,fsm=None):
        self.bot = bot
        self._events_collector = EventCollector()
        if not fsm:
            self.fsm = ffsm.MemoryFSM()
        else:
            self.fsm = fsm


        # Запрет на сообщения до закрытия формы (Статичное)
        @bot.message_handler(func=lambda message: True and self.fsm.check_already_form(message.chat.id))
        def cath_stop_freeze_events_on_idle(message):
            self.stop_freeze_event(message)

        def __check_already_input_only_from_callback_mode(user_id,from_idle=False):
            """ Валидация только евентов допустимых к заморозке """
            fsm_data = self.fsm.get_state(user_id)
            if from_idle:
                if ":".join(str(fsm_data.state).split(":")[0:2]) != FSM_FORM_IDE:
                    return False
            else:
                if fsm_data.state != FSM_GET_FIELD_VALUE:
                    return False

            form = BaseForm.form_loads(fsm_data.args.form)
            settings = self._get_form_settings(form,prepare_update=user_id)
            if fsm_data.args.from_callback and settings["FREEZE_MODE"]:
                return True
            return False


        # Запрет на сообщения до закрытия формы (Запрос значений)
        @bot.message_handler(func=lambda message: True and __check_already_input_only_from_callback_mode(message.chat.id))
        def cath_stop_freeze_events_on_from_callback_getting(message):
            self.stop_freeze_event(message)

        # Редактировать поле
        @self.bot.callback_query_handler(func=lambda call: True and (str(":".join(call.data.split(":")[0:2])) + ":{}") == FIELD_CLICK_CALLBACK_DATA_PATTERN)
        def cath_edit_callback_events(call):
            self.callback_events(call)

        # Отправка формы
        @self.bot.callback_query_handler(func=lambda call: True and (str(":".join(call.data.split(":")[0:2]))) == DEFAULT_SUBMIT_CALLBACK)
        def cath_submit_callback_events(call):
            self.submit_form(call)


        # Стандартная отмена ввода
        @self.bot.callback_query_handler(func=lambda call: True and call.data == DEFAULT_CANCEl_CALLBACK)
        def cath_deffault_cancel_callback_events(call):
            self.deffault_cancel_input(call)

        # Стандартное закрытие формы
        @self.bot.callback_query_handler(func=lambda call: True and call.data == DEFAULT_CANCEl_FORM_CALLBACK)
        def cath_deffault_close_form_callback_events(call):
            self.deffault_close_form(call)


        # Получить данные для поля (FROM_CALLBACK)
        @self.bot.callback_query_handler(func=lambda call: True and self.fsm.check_input_status(call.from_user.id) and (str(":".join(call.data.split(":")[0:2])) + ":{}") == DEFAULT_VALUE_FROM_CALLBACK_PATTERN,)
        def cath_callback_mode_input_events(call):
            self.callback_mode_input(call)

        # Получить данные для поля (FROM MESSAGE)
        @bot.message_handler(func=lambda message: True and self.fsm.check_input_status(message.from_user.id),content_types=all_content_types )
        def cath_msg_mode_input_events(message):
            self.msg_mode_input(message)



    def set_global(self,edit=False,read_only=False,missing_value=False):
        if edit:
            self.GLOBAL_EDIT_ICON = edit
        if read_only:
            self.GLOBAL_READ_ONLY_ICON = read_only
        if missing_value:
            self.GLOBAL_MISSING_VALUE_ICON = missing_value

    def form_submit_event(self,name):
        """ Декоратор обновлений отправки формы """
        def pre_decoration(in_func):
            self._events_collector.register_submit(name,in_func)
        return pre_decoration

    def form_cancel_event(self,name):
        """ Декоратор обновления закрытия формы """
        def pre_decoration(in_func):
            self._events_collector.register_cancel(name,in_func)
        return pre_decoration

    def form_event(self,name: str, action: list):
        """ Общий декоратор обновления формы """
        def pre_decoration(in_func):
            if "submit" in action:
                self._events_collector.register_submit(name,in_func)
            if "cancel":
                self._events_collector.register_cancel(name,in_func)
        return pre_decoration

    def global_submit(self):
        """ Глобальный евент для отправки формы, все формы будут отправляться сюда """
        def pre_decoration(in_func):
            self._events_collector._global_submit = in_func
        return pre_decoration

    def global_cancel(self):
        """ Глобальный евент для отмены формы, все отмены будут отправляться сюда"""
        def pre_decoration(in_func):
            self._events_collector._global_cancel = in_func
        return pre_decoration


    def to_submit_form(self,name,upd,form):
        if self._events_collector._global_submit:
            func = self._events_collector._global_submit
        else:
            func = self._events_collector.get_submit(name)
        func(upd,form)

    def to_cancel_form(self,name,upd,form):
        func = self._events_collector.get_cancel(name)
        if not func:
            if self._events_collector._global_cancel:
                func = self._events_collector._global_cancel
            else:
                # Евент не определён....
                return
        func(upd,form)

    def _get_form_settings(self,form,prepare_update=False,prepere_list = ["CANCEL_BUTTON_TEXT","STOP_FREEZE_TEXT","INVALID_INPUT_TEXT"]):
        settings = {}
        if self.GLOBAL_EDIT_ICON:
            settings["EDIT_ICON"] = self.GLOBAL_EDIT_ICON
        else:
            settings["EDIT_ICON"] = form.EDIT_ICON
        if self.GLOBAL_READ_ONLY_ICON:
            settings["READ_ONLY_ICON"] = self.GLOBAL_READ_ONLY_ICON
        else:
            settings["READ_ONLY_ICON"] = form.READ_ONLY_ICON
        if self.GLOBAL_MISSING_VALUE_ICON:
            settings["MISSING_VALUE_ICON"] = self.GLOBAL_MISSING_VALUE_ICON
        else:
            settings["MISSING_VALUE_ICON"] = form.MISSING_VALUE_ICON
        if self.GLOBAL_CANCEL_CALLBACK:
            settings["CANCEL_CALLBACK"] = self.GLOBAL_CANCEL_CALLBACK
        else:
            settings["CANCEL_CALLBACK"] = form.cancel_callback
        if self.GLOBAL_CANCELED_TEXT:
            settings["CANCELED_TEXT"] = self.GLOBAL_CANCELED_TEXT
        else:
            settings["CANCELED_TEXT"] = form.canceled_text
        if form.cancel_button_text:
            settings["CANCEL_BUTTON_TEXT"] = form.cancel_button_text
        elif self.GLOBAL_CANCEL_BUTTON_TEXT:
            settings["CANCEL_BUTTON_TEXT"] = self.GLOBAL_CANCEL_BUTTON_TEXT
        else:
            settings["CANCEL_BUTTON_TEXT"] = form.default_cancel_button_text
        if self.GLOBAL_SUBMIT_BUTTON_TEXT:
            settings["SUBMIT_BUTTON_TEXT"] = self.GLOBAL_SUBMIT_BUTTON_TEXT
        else:
            settings["SUBMIT_BUTTON_TEXT"] = form.submit_button_text
        if self.GLOBAL_CLOSE_FORM_BUT:
            settings["CLOSE_FORM_BUT"] = self.GLOBAL_CLOSE_FORM_BUT
        else:
            settings["CLOSE_FORM_BUT"] = form.close_form_but
        if self.GLOBAL_FREEZE_MODE:
            settings["FREEZE_MODE"] = self.GLOBAL_FREEZE_MODE
        else:
            settings["FREEZE_MODE"] = form.freeze_mode
        if form.stop_freeze_text:
            settings["STOP_FREEZE_TEXT"] = form.stop_freeze_text
        elif self.GLOBAL_STOP_FREEZE_TEXT:
            settings["STOP_FREEZE_TEXT"] = self.GLOBAL_STOP_FREEZE_TEXT
        else:
            settings["STOP_FREEZE_TEXT"] = form.default_stop_freeze_text
        if self.GLOBAL_LIFE_TIME:
            settings["LIFE_TIME"] = self.GLOBAL_LIFE_TIME
        else:
            settings["LIFE_TIME"] = form.life_time
        if form.input_not_valid:
            settings["INVALID_INPUT_TEXT"] = form.input_not_valid
        elif self.GLOBAL_INVALID_INPUT_TEXT:
            settings["INVALID_INPUT_TEXT"] = self.GLOBAL_INVALID_INPUT_TEXT
        else:
            settings["INVALID_INPUT_TEXT"] = form.default_input_not_valid
        if prepare_update:
            for prepere_keyname in prepere_list:
                if isinstance(settings[prepere_keyname], build_in_types.FunctionType):
                    settings[prepere_keyname] = settings[prepere_keyname](prepare_update)

        return settings


    def send_form(self,user_id: int,form,need_init=True):
        if need_init:
            form.init_form()
        if not isinstance(form,BaseForm):
            raise Expetion("form must be like BaseForm")
        keyboard = types.InlineKeyboardMarkup()
        fields_markup = form.get_fields()
        text = form.get_form_text()
        settings = self._get_form_settings(form,prepare_update=user_id)
        for f in fields_markup:
            k_text = ""
            if f["replace_icon"]:
                k_text += f["replace_icon"]
            elif f["value"]:
                k_text += settings["EDIT_ICON"]
            else:
                k_text += settings["MISSING_VALUE_ICON"]
            k_text += f["text"]
            key = types.InlineKeyboardButton(text=k_text, callback_data=f["callback_data"])
            keyboard.add(key)
        if form.is_ready_to_submit():
            submit_key = types.InlineKeyboardButton(text=settings["SUBMIT_BUTTON_TEXT"], callback_data=DEFAULT_SUBMIT_CALLBACK)
            keyboard.add(submit_key)
        if settings["CLOSE_FORM_BUT"]:
            cancel_key = types.InlineKeyboardButton(text=settings["CANCEL_BUTTON_TEXT"], callback_data=DEFAULT_CANCEl_FORM_CALLBACK)
            keyboard.add(cancel_key)
        idle_state = "{}:{}".format(FSM_FORM_IDE,form._form_id)
        parse_mode = None
        if form.form_title:
            parse_mode = "Markdown"
        msg = self.bot.send_message(user_id,text,reply_markup=keyboard,parse_mode=parse_mode,disable_web_page_preview=True)
        form.last_msg_id = msg.message_id
        self.fsm.set_state(int(user_id),idle_state,life_time = settings["LIFE_TIME"],form=form._form_dumps())
        return msg


    def callback_events(self,call):
        form_status = self.fsm.check_already_form(int(call.from_user.id))
        if not form_status:
            return
        state_data = self.fsm.get_state(int(call.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        if state_data.state.split(":")[2] != form._form_id:
            return
        f_id = call.data.split(":")[2]
        field = form.get_field_by_id(f_id)
        if not form or not field:
            return
        settings = self._get_form_settings(form,prepare_update=call.message.chat.id)
        text = field.input_text
        if field.value_from_callback:
            keyboard = field.create_variables_keys()
        else:
            keyboard = types.InlineKeyboardMarkup()
        cancel_key = types.InlineKeyboardButton(text=settings["CANCEL_BUTTON_TEXT"], callback_data=settings["CANCEL_CALLBACK"])
        if not field.without_system_key:
            keyboard.add(cancel_key)
        self.bot.delete_message(call.message.chat.id,call.message.message_id)
        msg = self.bot.send_message(call.from_user.id,text,reply_markup=keyboard)
        form.last_msg_id = msg.message_id
        self.fsm.set_state(call.from_user.id,FSM_GET_FIELD_VALUE,form=form._form_dumps(),field_id=field._id,from_callback=field.value_from_callback)

    def submit_form(self,call):
        form_status = self.fsm.check_already_form(int(call.from_user.id))
        if not form_status:
            return
        state_data = self.fsm.get_state(int(call.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        if not form.is_ready_to_submit():
            return
        if state_data.state.split(":")[2] != form._form_id:
            return
        form_to_upd = form.create_update_form_object(action="submit")
        form_valid_status = form.form_validator(call,form_to_upd)
        invalid_form_error = form.form_valid_error
        if isinstance(form_valid_status,str):
            invalid_form_error = form_valid_status
        if not form_valid_status or isinstance(form_valid_status,str):
            self.bot.answer_callback_query(callback_query_id=call.id,show_alert=True,text=invalid_form_error)
            return
        self.bot.delete_message(call.message.chat.id,call.message.message_id)
        self.fsm.reset_state(call.message.chat.id)
        self.to_submit_form(form.get_update_name(),call,form_to_upd)



    def deffault_cancel_input(self,call):
        if not self.fsm.check_input_status(call.from_user.id):
            return
        state_data = self.fsm.get_state(int(call.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        settings = self._get_form_settings(form,prepare_update=call.message.chat.id)
        idle_state = "{}:{}".format(FSM_FORM_IDE,form._form_id)
        self.fsm.set_state(int(call.from_user.id),idle_state,form=form._form_dumps())
        self.bot.delete_message(call.message.chat.id,call.message.message_id)
        self.send_form(call.from_user.id,form,need_init=False)

    def deffault_close_form(self,call):
        form_status = self.fsm.check_already_form(int(call.from_user.id))
        if not form_status:
            return
        state_data = self.fsm.get_state(int(call.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        if state_data.state.split(":")[2] != form._form_id:
            return
        form_to_upd = form.create_update_form_object(action="cancel")
        self.bot.delete_message(call.message.chat.id,call.message.message_id)
        self.fsm.reset_state(call.message.chat.id)
        self.to_cancel_form(form.get_update_name(),call,form_to_upd)

    def msg_mode_input(self,message):
        state_data = self.fsm.get_state(int(message.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        settings = self._get_form_settings(form,prepare_update=message.chat.id)
        f_id = state_data.args.field_id
        field = form.get_field_by_id(f_id)
        new_value = message.text
        valid = True
        if not field.validate(message):
            valid = False
        else:
            field.value = field.format_return_value(message)
        event = FormEvent("field_input",sub_event_type="msg",event_data=field)
        if not valid:
            event.event_type = "field_input_invalid"
        form.event_listener(event,form.create_update_form_object(action="event_callback"))
        msg = self.send_form(message.from_user.id,form,need_init=False)
        if not valid:
            error_text = settings["INVALID_INPUT_TEXT"]
            if field.error_message:
                error_text = field.error_message
            elif form.form_global_error_message:
                error_text = form.form_global_error_message
            self.bot.reply_to(message,error_text)

    def callback_mode_input(self,call):
        state_data = self.fsm.get_state(int(call.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        f_id = state_data.args.field_id
        field = form.get_field_by_id(f_id)
        if field.value_from_callback_manual_mode:
            field.manualy_handle_callback(self,call,form)
        else:
            new_value_id = call.data.split(":")[2]
            new_value = field.get_variable_data(new_value_id)
            field.value = field.format_return_value(new_value)
            self.bot.delete_message(call.message.chat.id,call.message.message_id)
        event = FormEvent("field_input",sub_event_type="callback",event_data=field)
        form.event_listener(event,form.create_update_form_object(action="event_callback"))
        if not field.value_from_callback_manual_mode:
            msg = self.send_form(call.from_user.id,form,need_init=False)


    def stop_freeze_event(self,message):
        state_data = self.fsm.get_state(int(message.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        settings = self._get_form_settings(form,prepare_update=message.chat.id)
        if settings["FREEZE_MODE"]:
            self.bot.send_message(message.chat.id,settings["STOP_FREEZE_TEXT"],reply_to_message_id=form.last_msg_id)


class BaseForm:
    """
        Основной класс формы:
            Все формы должны наследовать от него
    """

    MISSING_VALUE_ICON = "💢"
    READ_ONLY_ICON = '🔒'
    EDIT_ICON = '✏️'
    update_name = None
    custom_button = None

    freeze_mode = False
    close_form_but = False
    life_time = False
    form_hidden_data = None
    inited = False
    pre_inited = False

    cancel_callback = DEFAULT_CANCEl_CALLBACK
    form_close_callback = DEFAULT_CANCEl_FORM_CALLBACK

    submit_button_text = "Submit"
    cancel_button_text = None
    default_cancel_button_text = "Cancel"
    canceled_text = "Successfully canceled!"
    input_get_text = "Send new value:"
    input_not_valid = None
    default_input_not_valid = "Invalid input..."
    stop_freeze_text = None
    default_stop_freeze_text = "Close or submit form..."
    form_global_error_message = None
    form_valid_error = "Error! You may have filled in some of the fields incorrectly. ⚠️"
    form_title = None

    _answer = {}
    _form_hidden_list = []


    def __init__(self):
        pass

    def init_form(self):
        iter_dict = self.__dict__
        if not iter_dict:
            iter_dict = self.__class__.__dict__
        if not self.pre_inited:
            self.all_field = {}
        self.last_msg_id = None
        for atr in iter_dict:
            atr_data = getattr(self,atr)
            if not isinstance(atr_data,fields.Field):
                continue
            self.all_field[atr] = atr_data
        self._form_id = fields.Field._generate_id(6)
        self.form_data = self.form_hidden_data
        self.inited = True

    def field_from_dict(self,new_fields):
        """ Добавить поля к форме из словаря """
        if not self.inited:
            self.all_field = {}
        for f_name in new_fields:
            field = new_fields[f_name]
            self.all_field[f_name] = field
        self.pre_inited = True

    def _get_all_field(self,to_dict=False):
        if to_dict:
            return self.all_field
        return list(self.all_field.values())

    def form_validator(self,upd,form_data):
        return True

    def event_listener(self,event,form_data):
        return

    def hide_field(self,name):
        if name not in self._form_hidden_list:
            self._form_hidden_list.append(name)

    def show_field(self,name):
        if name in self._form_hidden_list:
            ind = self._form_hidden_list.index(name)
            del self._form_hidden_list[ind]

    def field_visable_status(self,name):
        return bool(name in self._form_hidden_list)


    def get_fields(self):
        all_field = self._get_all_field(to_dict=True)
        markup = []
        for f_name,f in all_field.items():
            if f_name in self._form_hidden_list:
                continue
            key = f.create_key()
            markup.append(key)
        return markup

    def get_field_by_id(self,f_id: str):
        all_field = self._get_all_field(to_dict=True)
        for f_name,f in all_field.items():
            if f._id == f_id:
                need_field = f
                need_field.name_in_form = f_name
                return need_field
        return False

    def get_field_by_name(self,f_name: str):
        all_field = self._get_all_field(to_dict=True)
        for f in all_field:
            if f == f_name:
                return all_field[f]
        return False

    def get_form_text(self):
        text = ""
        if self.form_title:
            text = "*"+str(self.form_title)+"*" + "\n\n"
        all_field = self._get_all_field(to_dict=True)
        for f_name,f in all_field.items():
            if f_name in self._form_hidden_list:
                continue
            value_format = f.message_text_data_format()
            if value_format == None:
                value_format = ""
            text += "{}: {}".format(f.title,value_format)
            if list(all_field.values())[-1] != f:
                text += "\n"
        return text

    def is_ready_to_submit(self):
        all_field = self._get_all_field(to_dict=True)
        for f_name,f in all_field.items():
            if f_name in self._form_hidden_list:
                continue
            if f.required and f.value == None:
                return False
        return True

    def get_update_name(self):
        return self.update_name

    def create_update_form_object(self,action=None):
        all_fields =  self._get_all_field(to_dict=True)
        out_map = {}
        for f in all_fields:
            out_map[f] = all_fields[f].value
        if action:
            out_map["update_action"] = action
        out_map["form_hidden_data"] = self.form_data
        return namedtuple(self.__class__.__name__, out_map.keys())(*out_map.values())

    def _form_dumps(self):
        return pickle.dumps(self)


    @staticmethod
    def form_loads(dumps_data):
        return pickle.loads(dumps_data)
