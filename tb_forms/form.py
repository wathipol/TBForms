from telebot import types
from . import fields
from .validators import all_content_types
from . import validators
from .tbf_types import FormEvent
from .tb_fsm import (
    DEFAULT_CANCEl_CALLBACK,
    DEFAULT_CANCEl_FORM_CALLBACK,
    DEFAULT_SKIP_CALLBACK,
    DEFAULT_BACK_CALLBACK
)
import types as build_in_types
from typing import Union, Optional
from collections import namedtuple
import pickle


class BaseForm:
    """
        Основной класс формы:
            Все формы должны наследовать от него
    """

    MISSING_VALUE_ICON = "💢"
    READ_ONLY_ICON = '🔒'
    EDIT_ICON = '✏️'
    FORM_IMG = None
    update_name = None
    custom_button = None

    freeze_mode = False
    default_auto_submit = False
    close_form_but = False
    life_time = False
    form_hidden_data = None
    inited = False
    pre_inited = False
    default_step_by_step = None

    cancel_callback = DEFAULT_CANCEl_CALLBACK
    back_callback = DEFAULT_BACK_CALLBACK
    skip_callback = DEFAULT_SKIP_CALLBACK
    form_close_callback = DEFAULT_CANCEl_FORM_CALLBACK

    submit_button_text = "Submit"
    cancel_button_text = None
    back_text = None
    default_cancel_button_text = "Cancel"
    canceled_text = "Successfully canceled!"
    input_get_text = "Send new value:"
    input_not_valid = None
    default_input_not_valid = "Invalid input..."
    stop_freeze_text = None
    step_by_step_skip_text = None
    default_step_by_step_skip_text = "➡️"
    step_by_step_back_text = None
    default_back_button_text = "🔙"
    default_stop_freeze_text = "Close or submit form..."
    form_global_error_message = None
    form_valid_error = "Error! You may have filled in some of the fields incorrectly. ⚠️"
    form_title = None

    _answer = {}
    _form_hidden_list = []
    _step_by_step = None
    _auto_submit = None

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
            atr_data = getattr(self, atr)
            if not isinstance(atr_data, fields.Field):
                continue
            self.all_field[atr] = atr_data
        self._form_id = fields.Field._generate_id(6)
        self._step_by_step = self.default_step_by_step
        self._auto_submit = self.default_auto_submit
        self.form_data = self.form_hidden_data
        self.inited = True

    def field_from_dict(self, new_fields):
        """ Добавить поля к форме из словаря """
        if not self.inited:
            self.all_field = {}
        for f_name in new_fields:
            field = new_fields[f_name]
            self.all_field[f_name] = field
        self.pre_inited = True

    def _get_all_field(self, to_dict=False):
        if to_dict:
            return self.all_field
        return list(self.all_field.values())

    def form_validator(self, upd: Union[types.CallbackQuery, int], form_data):
        """ Form validation before submit
                upd is types.CallbackQuery object or chat_id: int if step_by_step mode is True
        """
        return True

    def event_listener(self, event, form_data):
        return

    def hide_field(self, name):
        if name not in self._form_hidden_list:
            self._form_hidden_list.append(name)

    def show_field(self, name):
        if name in self._form_hidden_list:
            ind = self._form_hidden_list.index(name)
            del self._form_hidden_list[ind]

    def field_visable_status(self, name):
        return bool(name in self._form_hidden_list)

    def get_fields(self):
        all_field = self._get_all_field(to_dict=True)
        markup = []
        for f_name, f in all_field.items():
            if f_name in self._form_hidden_list:
                continue
            key = f.create_key()
            markup.append(key)
        return markup

    def get_field_by_id(self, f_id: str):
        all_field = self._get_all_field(to_dict=True)
        for f_name, f in all_field.items():
            if f._id == f_id:
                need_field = f
                need_field.name_in_form = f_name
                return need_field
        return False

    def get_field_by_name(self, f_name: str):
        all_field = self._get_all_field(to_dict=True)
        for f in all_field:
            if f == f_name:
                return all_field[f]
        return False

    def get_field_by_index(self, index: int):
        all_field = self._get_all_field(to_dict=True)
        n_key = list(all_field.keys())[index]
        return all_field[n_key]

    def get_field_index(self, field):
        all_field = self._get_all_field(to_dict=True)
        ind = 0
        for f_t, f in all_field.items():
            if f == field:
                return ind
            ind += 1
        raise IndexError("Field not found")
            

    def get_form_text(self):
        text = ""
        if self.form_title:
            text = "<b>" + str(self.form_title) + "</b>" + "\n\n"
        all_field = self._get_all_field(to_dict=True)
        for f_name, f in all_field.items():
            if f_name in self._form_hidden_list:
                continue
            value_format = f.message_text_data_format()
            if value_format is None:
                value_format = ""
            text += "{}: {}".format(f.title, value_format)
            if list(all_field.values())[-1] != f:
                text += "\n"
        return text

    def is_ready_to_submit(self, with_optional_fields: bool = False):
        all_field = self._get_all_field(to_dict=True)
        for f_name, f in all_field.items():
            if f_name in self._form_hidden_list:
                continue
            if f.required and f.value is None:
                return False
            elif f.value is None and not f.required and with_optional_fields is True:
                if f._skiped is False:
                    return False
        return True

    def get_update_name(self):
        return self.update_name

    def create_update_form_object(self, action=None):
        all_fields = self._get_all_field(to_dict=True)
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