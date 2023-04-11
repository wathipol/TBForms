from telebot import types
from . import fields
from . import tb_fsm as ffsm
from .validators import all_content_types
from . import validators
from .tbf_types import FormEvent
from .tb_fsm import (
    TB_FORM_TAG,
    DEFAULT_CANCEl_CALLBACK,
    FIELD_CLICK_CALLBACK_DATA_PATTERN,
    FSM_FORM_IDE,
    DEFAULT_SUBMIT_CALLBACK,
    FSM_GET_FIELD_VALUE,
    DEFAULT_CANCEl_FORM_CALLBACK,
    DEFAULT_VALUE_FROM_CALLBACK_PATTERN,
    DEFAULT_SKIP_CALLBACK,
    DEFAULT_BACK_CALLBACK
)
from .form import BaseForm
from collections import namedtuple
import pickle
import logging
import types as build_in_types

__version__ = "0.9.11"


class EventCollector:
    _submit_collector = {}
    _cancel_collector = {}
    _global_cancel = None
    _global_submit = None

    def register_submit(self, name, func):
        self._submit_collector[name] = func

    def register_cancel(self, name, func):
        self._cancel_collector[name] = func

    def get_submit(self, name):
        if name in list(self._submit_collector.keys()):
            return self._submit_collector[name]
        return False

    def get_cancel(self, name):
        if name in list(self._cancel_collector.keys()):
            return self._cancel_collector[name]
        return False


class TelebotForms:
    """ Основной класс дополнения """
    GLOBAL_MISSING_VALUE_ICON = None
    GLOBAL_READ_ONLY_ICON = None
    GLOBAL_EDIT_ICON = None
    GLOBAL_CANCEL_BUTTON_TEXT = None
    GLOBAL_CANCEL_CALLBACK = None
    GLOBAL_BACK_CALLBACK = None
    GLOBAL_SKIP_CALLBACK = None
    GLOBAL_CANCELED_TEXT = None
    GLOBAL_SUBMIT_BUTTON_TEXT = None
    GLOBAL_CLOSE_FORM_BUT = None
    GLOBAL_FREEZE_MODE = None
    GLOBAL_AUTO_SUBMIT = None
    GLOBAL_STOP_FREEZE_TEXT = None
    GLOBAL_LIFE_TIME = None
    GLOBAL_INVALID_INPUT_TEXT = None
    GLOBAL_FORM_IMG = None
    GLOBAL_STEP_BY_STEP = None
    GLOBAL_BACK_TEXT = None
    GLOBAL_STEP_BY_STEP_SKIP_TEXT = None

    def __init__(self, bot, fsm=None):
        self.bot = bot
        self._events_collector = EventCollector()
        if not fsm:
            self.fsm = ffsm.MemoryFSM()
        else:
            self.fsm = fsm
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Запрет на сообщения до закрытия формы (Статичное)
        @bot.message_handler(func=lambda message: True and self.fsm.check_already_form(message.chat.id))
        def cath_stop_freeze_events_on_idle(message):
            self.stop_freeze_event(message)

        def __check_already_input_only_from_callback_mode(user_id, from_idle=False):
            """ Валидация только евентов допустимых к заморозке """
            fsm_data = self.fsm.get_state(user_id)
            if from_idle:
                if ":".join(str(fsm_data.state).split(":")[0:2]) != FSM_FORM_IDE:
                    return False
            else:
                if fsm_data.state != FSM_GET_FIELD_VALUE:
                    return False

            form = BaseForm.form_loads(fsm_data.args.form)
            settings = self._get_form_settings(form, prepare_update=user_id)
            if hasattr(fsm_data.args, 'from_callback'):
                if fsm_data.args.from_callback and settings["FREEZE_MODE"]:
                    return True
            return False

        # Запрет на сообщения до закрытия формы (Запрос значений)
        @bot.message_handler(
            func=lambda message: True and __check_already_input_only_from_callback_mode(message.chat.id))
        def cath_stop_freeze_events_on_from_callback_getting(message):
            self.stop_freeze_event(message)

        # Редактировать поле
        @self.bot.callback_query_handler(
            func=lambda call: True and (
                str(":".join(call.data.split(":")[0:2])) + ":{}") == FIELD_CLICK_CALLBACK_DATA_PATTERN)
        def cath_edit_callback_events(call):
            self.callback_events(call)

        # Отправка формы
        @self.bot.callback_query_handler(
            func=lambda call: True and (
                str(":".join(call.data.split(":")[0:2]))) == DEFAULT_SUBMIT_CALLBACK)
        def cath_submit_callback_events(call):
            self.submit_form(call)

        # Стандартная отмена ввода
        @self.bot.callback_query_handler(
            func=lambda call: True and call.data == DEFAULT_CANCEl_CALLBACK)
        def cath_deffault_cancel_callback_events(call):
            self.deffault_cancel_input(call)

        # Стандартный пропуск не обязательного поля в режиме step-by-step
        @self.bot.callback_query_handler(
            func=lambda call: True and self.fsm.check_input_status(call.from_user.id) and (
                str(":".join(call.data.split(":")[0:2])) + ":{}") == DEFAULT_SKIP_CALLBACK,
        )
        def cath_deffault_skip_callback_events(call):
            self.deffault_skip_input(call)

        # Стандартное возвращение назад в режиме step-by-step 
        @self.bot.callback_query_handler(
            func=lambda call: True and (
                self.fsm.check_input_status(call.from_user.id) or self.fsm.check_already_form(int(call.from_user.id))) and (
                str(":".join(call.data.split(":")[0:2])) + ":{}") == DEFAULT_BACK_CALLBACK,
        )
        def cath_deffault_back_callback_events(call):
            self.deffault_back_input(call)

        # Стандартное закрытие формы
        @self.bot.callback_query_handler(
            func=lambda call: True and ":".join(str(call.data).split(":")[0:2]) == DEFAULT_CANCEl_FORM_CALLBACK)
        def cath_deffault_close_form_callback_events(call):
            self.deffault_close_form(call)

        # Получить данные для поля (FROM_CALLBACK)
        @self.bot.callback_query_handler(
            func=lambda call: True and self.fsm.check_input_status(call.from_user.id) and (
                str(":".join(call.data.split(":")[0:2])) + ":{}") == DEFAULT_VALUE_FROM_CALLBACK_PATTERN,
        )
        def cath_callback_mode_input_events(call):
            self.callback_mode_input(call)

        # Получить данные для поля (FROM MESSAGE)
        @bot.message_handler(
            func=lambda message: True and self.fsm.check_input_status(
                message.from_user.id), content_types=all_content_types)
        def cath_msg_mode_input_events(message):
            self.msg_mode_input(message)

    def set_global(self, edit=False, read_only=False, missing_value=False):
        if edit:
            self.GLOBAL_EDIT_ICON = edit
        if read_only:
            self.GLOBAL_READ_ONLY_ICON = read_only
        if missing_value:
            self.GLOBAL_MISSING_VALUE_ICON = missing_value

    def form_submit_event(self, name):
        """ Декоратор обновлений отправки формы """
        def pre_decoration(in_func):
            self._events_collector.register_submit(name, in_func)
        return pre_decoration

    def form_cancel_event(self, name):
        """ Декоратор обновления закрытия формы """
        def pre_decoration(in_func):
            self._events_collector.register_cancel(name, in_func)
        return pre_decoration

    def form_event(self, name: str, action: list):
        """ Общий декоратор обновления формы """
        def pre_decoration(in_func):
            if "submit" in action:
                self._events_collector.register_submit(name, in_func)
            if "cancel":
                self._events_collector.register_cancel(name, in_func)
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

    def to_submit_form(self, name, upd, form):
        if self._events_collector._global_submit:
            func = self._events_collector._global_submit
        else:
            func = self._events_collector.get_submit(name)
        func(upd, form)

    def to_cancel_form(self, name, upd, form):
        func = self._events_collector.get_cancel(name)
        if not func:
            if self._events_collector._global_cancel:
                func = self._events_collector._global_cancel
            else:
                # Евент не определён....
                return
        func(upd, form)

    def _get_form_settings(
            self, form,
            prepare_update=False,
            prepere_list=["CANCEL_BUTTON_TEXT", "STOP_FREEZE_TEXT", "INVALID_INPUT_TEXT"]):
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
        if self.GLOBAL_BACK_CALLBACK is not None:
            settings["BACK_CALLBACK"] = self.GLOBAL_BACK_CALLBACK
        else:
            settings["BACK_CALLBACK"] = form.back_callback
        if self.GLOBAL_SKIP_CALLBACK is not None:
            settings["SKIP_CALLBACK"] = self.GLOBAL_SKIP_CALLBACK
        else:
            settings["SKIP_CALLBACK"] = form.skip_callback
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
        if form.back_text is not None:
            settings["BACK_TEXT"] = form.back_text
        elif self.GLOBAL_BACK_TEXT is not None:
            settings["BACK_TEXT"] = self.GLOBAL_BACK_TEXT
        else:
            settings["BACK_TEXT"] = form.default_back_button_text
        if form.step_by_step_skip_text is not None:
            settings["STEP_BY_STEP_SKIP_TEXT"] = form.step_by_step_skip_text
        elif self.GLOBAL_STEP_BY_STEP_SKIP_TEXT is not None:
            settings["STEP_BY_STEP_SKIP_TEXT"] = self.GLOBAL_STEP_BY_STEP_SKIP_TEXT
        else:
            settings["STEP_BY_STEP_SKIP_TEXT"] = form.default_step_by_step_skip_text
        if form.FORM_IMG:
            settings["FORM_IMG"] = form.FORM_IMG
        else:
            settings["FORM_IMG"] = self.GLOBAL_FORM_IMG
        
        if self.GLOBAL_STEP_BY_STEP is not None:
            settings["STEP_BY_STEP"] = self.GLOBAL_STEP_BY_STEP
        else:
            settings["STEP_BY_STEP"] = False if form._step_by_step is None else form._step_by_step
        if self.GLOBAL_AUTO_SUBMIT is not None:
            settings["AUTO_SUBMIT"] = self.GLOBAL_AUTO_SUBMIT
        else:
            settings["AUTO_SUBMIT"] = False if form._auto_submit is None else form._auto_submit

        if prepare_update:
            for prepere_keyname in prepere_list:
                if isinstance(settings[prepere_keyname], build_in_types.FunctionType):
                    settings[prepere_keyname] = settings[prepere_keyname](prepare_update)

        return settings

    def to_step_input(self, user_id: int, form, settings: dict):
        if settings is None:
            settings = self._get_form_settings(form, prepare_update=user_id)
        if settings["STEP_BY_STEP"] is not True:
            raise TypeError("is not step-by-step form")

        current_input = None
        for t, f in form.all_field.items():
            if f.value is None and f._skiped is False:
                current_input = f
                break
        if current_input is None:
            if settings["AUTO_SUBMIT"] is True:
                self.submit_form(int(user_id))
            else:
                keyboard = types.InlineKeyboardMarkup()
                text = form.get_form_text()
                idle_state = "{}:{}".format(FSM_FORM_IDE, form._form_id)
                submit_key = types.InlineKeyboardButton(
                    text=settings["SUBMIT_BUTTON_TEXT"], callback_data=DEFAULT_SUBMIT_CALLBACK)
                keyboard.add(submit_key)
                back_field = form.get_field_by_index(-1)
                back_key = types.InlineKeyboardButton(
                    text=settings["BACK_TEXT"],
                    callback_data=str(settings["BACK_CALLBACK"]).format(back_field._id))
                keyboard.add(back_key)
                if settings["CLOSE_FORM_BUT"]:
                    cancel_callback = "{}:{}".format(DEFAULT_CANCEl_FORM_CALLBACK, form._form_id)
                    cancel_key = types.InlineKeyboardButton(
                        text=settings["CANCEL_BUTTON_TEXT"], callback_data=cancel_callback)
                    keyboard.add(cancel_key)
                parse_mode = None
                if form.form_title:
                    parse_mode = "HTML"
                if not settings["FORM_IMG"]:
                    msg = self.bot.send_message(
                        user_id, text,
                        reply_markup=keyboard, parse_mode=parse_mode, disable_web_page_preview=True)
                else:
                    msg = self.bot.send_photo(
                        user_id, settings["FORM_IMG"],
                        caption=text, reply_markup=keyboard, parse_mode=parse_mode)
                form.last_msg_id = msg.message_id
                self.fsm.set_state(
                    int(user_id), idle_state,
                    life_time=settings["LIFE_TIME"], form=form._form_dumps())
            return
        self.to_input_state(form, current_input, settings, int(user_id))

    def send_form(
            self, user_id: int, form,
            step_by_step: bool = None, auto_submit: bool = None, need_init=True):
        if not isinstance(form, BaseForm):
            raise TypeError("form must be BaseForm object")
        elif need_init:
            form.init_form()
        if step_by_step is not None:
            form._step_by_step = step_by_step
        if auto_submit is not None:
            form._auto_submit = auto_submit
        keyboard = types.InlineKeyboardMarkup()
        fields_markup = form.get_fields()
        text = form.get_form_text()
        settings = self._get_form_settings(form, prepare_update=user_id)
        idle_state = "{}:{}".format(FSM_FORM_IDE, form._form_id)
        if settings["STEP_BY_STEP"] is True:
            self.to_step_input(user_id, form,settings)
            return
        for f in fields_markup:
            k_text = ""
            if f["replace_icon"]:
                k_text += f["replace_icon"]
            elif f["value"] is not None:
                k_text += settings["EDIT_ICON"]
            else:
                k_text += settings["MISSING_VALUE_ICON"]
            k_text += f["text"]
            key = types.InlineKeyboardButton(text=k_text, callback_data=f["callback_data"])
            keyboard.add(key)
        if form.is_ready_to_submit():
            if settings["AUTO_SUBMIT"] is True and form.is_ready_to_submit(
                    with_optional_fields=True):
                self.fsm.set_state(
                    int(user_id), idle_state,
                    life_time=settings["LIFE_TIME"], form=form._form_dumps())
                self.submit_form(int(user_id))
                return
            submit_key = types.InlineKeyboardButton(
                text=settings["SUBMIT_BUTTON_TEXT"], callback_data=DEFAULT_SUBMIT_CALLBACK)
            keyboard.add(submit_key)
        if settings["CLOSE_FORM_BUT"]:
            cancel_callback = "{}:{}".format(DEFAULT_CANCEl_FORM_CALLBACK, form._form_id)
            cancel_key = types.InlineKeyboardButton(
                text=settings["CANCEL_BUTTON_TEXT"], callback_data=cancel_callback)
            keyboard.add(cancel_key)
        parse_mode = None
        if form.form_title:
            parse_mode = "HTML"
        if not settings["FORM_IMG"]:
            msg = self.bot.send_message(
                user_id, text,
                reply_markup=keyboard, parse_mode=parse_mode, disable_web_page_preview=True)
        else:
            msg = self.bot.send_photo(
                user_id, settings["FORM_IMG"],
                caption=text, reply_markup=keyboard, parse_mode=parse_mode)
        form.last_msg_id = msg.message_id
        self.fsm.set_state(
            int(user_id), idle_state,
            life_time=settings["LIFE_TIME"], form=form._form_dumps())
        return msg

    def to_input_state(self, form, field, settings, update):
        text = field.input_text
        if field.value_from_callback:
            keyboard = field.create_variables_keys()
        else:
            keyboard = types.InlineKeyboardMarkup()
        cancel_key = types.InlineKeyboardButton(
            text=settings["BACK_TEXT"], callback_data=settings["CANCEL_CALLBACK"])

        if not field.without_system_key:
            if field.required is False and settings["STEP_BY_STEP"] is True:
                skip_key = types.InlineKeyboardButton(
                    text=settings["STEP_BY_STEP_SKIP_TEXT"],
                    callback_data=str(settings["SKIP_CALLBACK"]).format(field._id))
                keyboard.add(skip_key)
            if settings["STEP_BY_STEP"] is True and form.get_field_by_index(0) != field:
                back_key = types.InlineKeyboardButton(
                    text=settings["BACK_TEXT"],
                    callback_data=str(settings["BACK_CALLBACK"]).format(field._id))
                keyboard.add(back_key)
            if settings["STEP_BY_STEP"] is not True:
                keyboard.add(cancel_key)
            else:
                if form.get_field_by_index(0) == field:
                    if settings["CLOSE_FORM_BUT"]:
                        form_cancel_callback = "{}:{}".format(DEFAULT_CANCEl_FORM_CALLBACK, form._form_id)
                        form_cancel_key = types.InlineKeyboardButton(
                            text=settings["CANCEL_BUTTON_TEXT"], callback_data=form_cancel_callback)
                        keyboard.add(form_cancel_key)
        field.before_input_update(self, form, update)
        chat_id = None
        msg_id = None
        if isinstance(update, types.Message):
            chat_id = update.chat.id
            msg_id = update.message_id
        elif isinstance(update, types.CallbackQuery):
            chat_id = update.message.chat.id
            msg_id = update.message.message_id
        elif isinstance(update, int):
            chat_id = update
        if chat_id is None:
            raise ValueError("update object is None")
        elif msg_id is not None:
            try:
                self.bot.delete_message(chat_id, msg_id)
            except Exception as e:
                pass 
        msg = self.bot.send_message(chat_id, text, reply_markup=keyboard)
        form.last_msg_id = msg.message_id
        self.fsm.set_state(
            chat_id, FSM_GET_FIELD_VALUE,
            form=form._form_dumps(), field_id=field._id, from_callback=field.value_from_callback)


    def callback_events(self, call):
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
        settings = self._get_form_settings(form, prepare_update=call.message.chat.id)
        self.to_input_state(form, field, settings, call)

    def submit_form(self, call, r_msg_id: int = None):
        chat_id = None
        msg_id = r_msg_id
        if isinstance(call, types.CallbackQuery):
            chat_id = int(call.message.chat.id)
            if r_msg_id is None:
                msg_id = int(call.message.message_id)
        elif isinstance(call, int):
            chat_id = call
        else:
            raise TypeError("call must be CallbackQuery object")
        form_status = self.fsm.check_already_form(chat_id)
        if not form_status:
            self.logger.error("Form not in idle state for submit")
            return
        state_data = self.fsm.get_state(chat_id)
        form = BaseForm.form_loads(state_data.args.form)
        if not form.is_ready_to_submit():
            self.logger.error("Form not ready to submit")
            return
        if state_data.state.split(":")[2] != form._form_id:
            return
        form_to_upd = form.create_update_form_object(action="submit")
        form_valid_status = form.form_validator(call if msg_id is not None else chat_id, form_to_upd)
        invalid_form_error = form.form_valid_error
        if isinstance(form_valid_status, str):
            invalid_form_error = form_valid_status
        if not form_valid_status or isinstance(form_valid_status, str):
            self.bot.answer_callback_query(
                callback_query_id=call.id, show_alert=True, text=invalid_form_error)
            return
        if msg_id is not None:
            self.bot.delete_message(chat_id, msg_id)
        self.fsm.reset_state(chat_id)
        self.to_submit_form(form.get_update_name(), call if msg_id is not None else chat_id, form_to_upd)

    def deffault_cancel_input(self, call):
        if not self.fsm.check_input_status(call.from_user.id):
            return
        state_data = self.fsm.get_state(int(call.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        settings = self._get_form_settings(form, prepare_update=call.message.chat.id)
        idle_state = "{}:{}".format(FSM_FORM_IDE, form._form_id)
        self.fsm.set_state(int(call.from_user.id), idle_state, form=form._form_dumps())
        self.bot.delete_message(call.message.chat.id, call.message.message_id)
        self.send_form(call.from_user.id, form, need_init=False)
    
    def deffault_back_input(self, call):
        state_data = self.fsm.get_state(int(call.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        settings = self._get_form_settings(form, prepare_update=call.message.chat.id)
        if not settings["STEP_BY_STEP"]:
            return
        f_id = call.data.split(":")[2]
        field = form.get_field_by_id(f_id)
        back_field = form.get_field_by_index(form.get_field_index(field) - 1)
        field.value = None
        back_field.value = None
        idle_state = "{}:{}".format(FSM_FORM_IDE, form._form_id)
        self.fsm.set_state(int(call.from_user.id), idle_state, form=form._form_dumps())
        self.bot.delete_message(call.message.chat.id, call.message.message_id)
        self.send_form(call.from_user.id, form, need_init=False)   

    def deffault_skip_input(self, call):
        if not self.fsm.check_input_status(call.from_user.id):
            return
        state_data = self.fsm.get_state(int(call.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        settings = self._get_form_settings(form, prepare_update=call.message.chat.id)
        if not settings["STEP_BY_STEP"]:
            return
        f_id = call.data.split(":")[2]
        field = form.get_field_by_id(f_id)
        field._skiped = True
        idle_state = "{}:{}".format(FSM_FORM_IDE, form._form_id)
        self.fsm.set_state(int(call.from_user.id), idle_state, form=form._form_dumps())
        self.bot.delete_message(call.message.chat.id, call.message.message_id)
        self.send_form(call.from_user.id, form, need_init=False)


    def deffault_close_form(self, call):
        form_status = self.fsm.check_already_form(int(call.from_user.id), any_tbf=True)
        if not form_status:
            return
        state_data = self.fsm.get_state(int(call.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        if str(call.data).split(":")[2] != form._form_id:
            return
        settings = self._get_form_settings(form, prepare_update=call.message.chat.id)
        if settings["STEP_BY_STEP"] is True:
            try:
                self.bot.delete_message(call.message.chat.id, int(form.last_msg_id))
            except Exception as e:
                pass
        form_to_upd = form.create_update_form_object(action="cancel")
        try:
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            pass
        self.fsm.reset_state(call.message.chat.id)
        self.to_cancel_form(form.get_update_name(), call, form_to_upd)

    def msg_mode_input(self, message):
        state_data = self.fsm.get_state(int(message.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        settings = self._get_form_settings(form, prepare_update=message.chat.id)
        f_id = state_data.args.field_id
        field = form.get_field_by_id(f_id)

        if field.value_from_message_manual_mode:
            field.manualy_handle_message(self, message, form)
            return
        field.after_input_update(self, form, message)
        new_value = message.text
        valid = True
        if not field.validate(message):
            valid = False
        else:
            field.value = field.format_return_value(message)
        event = FormEvent("field_input", sub_event_type="msg", event_data=field)
        if not valid:
            event.event_type = "field_input_invalid"
        form.event_listener(event, form.create_update_form_object(action="event_callback"))
        msg = self.send_form(message.from_user.id, form, need_init=False)
        if not valid:
            error_text = settings["INVALID_INPUT_TEXT"]
            if field.error_message:
                error_text = field.error_message
            elif form.form_global_error_message:
                error_text = form.form_global_error_message
            self.bot.reply_to(message, error_text)

    def callback_mode_input(self, call):
        state_data = self.fsm.get_state(int(call.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        f_id = state_data.args.field_id
        field = form.get_field_by_id(f_id)
        if field.value_from_callback_manual_mode:
            field.manualy_handle_callback(self, call, form)
            return
        field.after_input_update(self, form, call)
        new_value_id = call.data.split(":")[2]
        new_value = field.get_variable_data(new_value_id)
        field.value = field.format_return_value(new_value)
        self.bot.delete_message(call.message.chat.id, call.message.message_id)
        event = FormEvent("field_input", sub_event_type="callback", event_data=field)
        form.event_listener(event, form.create_update_form_object(action="event_callback"))
        msg = self.send_form(call.from_user.id, form, need_init=False)

    def stop_freeze_event(self, message):
        state_data = self.fsm.get_state(int(message.from_user.id))
        form = BaseForm.form_loads(state_data.args.form)
        settings = self._get_form_settings(form, prepare_update=message.chat.id)
        if settings["FREEZE_MODE"]:
            self.bot.send_message(
                message.chat.id, settings["STOP_FREEZE_TEXT"], reply_to_message_id=form.last_msg_id)
