import random
import string
import dill
from datetime import datetime, date, timedelta, time
from . import validators as fvalidators
from .validators import all_content_types,Validator
from .tbf_types import FormEvent
from telebot import types
from typing import Optional, List
from .tb_fsm import (
    TB_FORM_TAG,DEFAULT_CANCEl_CALLBACK,
    FIELD_CLICK_CALLBACK_DATA_PATTERN,
    DEFAULT_VALUE_FROM_CALLBACK_PATTERN,
    FSM_GET_FIELD_VALUE,
    FSM_FORM_IDE
)


def split_list(arr, wanted_parts=1):
    """Разбить список на подсписки"""
    arrs = []
    while len(arr) > wanted_parts:
        pice = arr[:wanted_parts]
        arrs.append(pice)
        arr = arr[wanted_parts:]
    arrs.append(arr)
    return arrs



def islambda(v):
    LAMBDA = lambda:0
    return isinstance(v, type(LAMBDA)) and v.__name__ == LAMBDA.__name__


class DillPickle:
    """ Обёртка для сериализации лямбда функций и других типов без поддержки """
    def __init__(self, e):
        self.e = e

    def __getstate__(self):
        return dill.dumps(self.e)
    def __setstate__(self, state):
        self.e = dill.loads(state)

    def __call__(self, *args, **kwargs):
        return self.e(*args, **kwargs)


class Field:
    """ Основной класс поля ввода """
    _id_len = 6

    @staticmethod
    def _generate_id(length):
        return ''.join(random.choice(string.ascii_letters) for i in range(length))

    def _fix_validators_type(self,validators):
        valid_list = []
        for validator in validators:
            if islambda(validator):
                valid_list.append(DillPickle(validator))
                continue
            valid_list.append(validator)
        return valid_list


    def __init__(self,title=None,input_text=None,validators=[],required=True,read_only=False,value_from_callback=False,error_message=None,default_value=None,field_hidden_data=None):
        self.title = title
        self.input_text = input_text
        self.validators = validators
        self.required = required
        self.read_only = read_only
        self._id = Field._generate_id(self._id_len)
        self.value_from_callback = value_from_callback
        self.value_from_callback_manual_mode = False
        self.value_from_message_manual_mode = False
        self.without_system_key = False
        self.value = default_value
        self.variable_data = {}
        self.error_message = error_message
        self.validators = self._fix_validators_type(self.validators)
        self.field_hidden_data = field_hidden_data
        self._skiped: bool = False

    def format_return_value(self,upd):
        if self.value_from_callback:
            return upd
        return upd.text

    def create_key(self):
        callback_data = FIELD_CLICK_CALLBACK_DATA_PATTERN.format(self._id)
        return {"text":self.title,"callback_data":callback_data,"value":self.value,"replace_icon":self.replace_field_icon()}

    def validate(self,upd):
        if not self.field_validator(upd):
            return False
        for validator in self.validators:
            if isinstance(validator,Validator):
                if not validator.validate(upd):
                    return False
            else:
                if not hasattr(validator, '__call__'):
                    continue
                if not validator(upd):
                    return False
        return True

    def before_input_update(self,tbf,form,update):
        pass

    def after_input_update(self,tbf,form,update):
        pass

    def field_validator(self,upd):
        return True

    def _append_variable_data(self,data) -> str:
        v_id = Field._generate_id(self._id_len)
        self.variable_data[v_id] = data
        return v_id

    def get_variable_data(self,v_id: str):
        if v_id in list(self.variable_data.keys()):
            return self.variable_data[v_id]

    def manualy_handle_callback(self,tbf,call,form):
        pass

    def manualy_handle_message(self,tbf,message,form):
        pass


    def create_variables_keys(self):
        """При использовании режима value_from_callback,
            Этот метод нужно переопределить для создания клавиатуры выбора
        """
        pass

    def message_text_data_format(self) -> str:
        """ Форматирование значения для текста в форме """
        return self.value

    def replace_field_icon(self) -> str:
        """ Замена иконки на кнопке """
        pass



class StrField(Field):
    def __init__(self,title=None,input_text=None,validators=[],required=True,read_only=False,error_message=None,min_len=None,max_len=None,only_latin=False,white_list=[],black_list=[],block_number=False,only_white_list=False,default_value=None,field_hidden_data=None):
        all_validators = [fvalidators.StringValidator(min_len=min_len,max_len=max_len,only_latin=only_latin,white_list=white_list,black_list=black_list,block_number=block_number,only_white_list=only_white_list)]
        for validator in validators:
            all_validators.append(validator)
        super().__init__(title=title,input_text=input_text,validators=all_validators,required=required,read_only=read_only,error_message=error_message,default_value=default_value,field_hidden_data=field_hidden_data)



class MediaField(Field):
    TYPES_ICON = {
        "photo":"🖼",
        "video":"📹",
        "document":"📄",
        "audio":"🎧",
        "text":"💬"
    }


    def __init__(self,title=None,input_text=None,validators=[],required=True,read_only=False,error_message=None,valid_types=[],caption_required=False,only_text_aviable=False,field_hidden_data=None):
        self.valid_types = valid_types
        self.media_validator = fvalidators.isMedia(valid_types=valid_types,caption_required=caption_required,only_text_aviable=only_text_aviable)
        all_validators = [self.media_validator]
        for validator in validators:
            all_validators.append(validator)
        super().__init__(title=title,input_text=input_text,validators=all_validators,required=required,read_only=read_only,error_message=error_message,field_hidden_data=field_hidden_data)


    def format_return_value(self,upd):
        return self.media_validator.get_media_data(upd)

    def message_text_data_format(self):
        if self.value == None:
            return self.value
        need_type = self.value.media_type
        if need_type in list(self.TYPES_ICON.keys()):
            return self.TYPES_ICON[need_type]
        else:
            return "<{}>".format(need_type)


    def replace_field_icon(self):
        if not self.valid_types:
            return
        elif len(self.valid_types) == 1:
            need_type = self.valid_types[0]
            if need_type in list(self.TYPES_ICON.keys()):
                return self.TYPES_ICON[need_type]





class NumberField(Field):

    def __init__(self,title=None,input_text=None,only_int=False,min_num=None,max_num=None,input_range=(1,99),custom_key_list=None,key_mode=False,validators=[],required=True,read_only=False,error_message=None,default_value=None,field_hidden_data=None):
        self.only_int = only_int
        all_validators = [fvalidators.isNumber(only_int=only_int,min_num=min_num,max_num=max_num)]
        for validator in validators:
            all_validators.append(validator)
        self.key_mode = key_mode
        super().__init__(title=title,input_text=input_text,validators=all_validators,required=required,read_only=read_only,value_from_callback=self.key_mode,error_message=error_message,default_value=default_value,field_hidden_data=field_hidden_data)
        if self.key_mode:
            if custom_key_list:
                self.key_range = custom_key_list
            else:
                self.key_range = input_range
                if (self.key_range[1] > 99) or (self.key_range[0] == 0 and self.key_range[1] == 99):
                    raise Exception("ArgumentError","Количество кнопок не может превышать 98")

    def format_return_value(self, upd):
        if self.key_mode:
            get_value = upd
        else:
            get_value = upd.text
        format_value = float(get_value)
        if self.only_int:
            return int(format_value)
        return format_value

    def create_variables_keys(self):
        keyboard = types.InlineKeyboardMarkup()
        key_list = []
        for i in range(self.key_range[0],self.key_range[1]):
            v_id = self._append_variable_data(i)
            key = types.InlineKeyboardButton(text=i, callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format(v_id))
            key_list.append(key)
        for row in split_list(key_list,8):
            keyboard.row(*row)
        return keyboard


class BooleanField(Field):
    true_icon = "✅"
    false_icon = "❌"

    def __init__(self,title=None,input_text=None,required=True,read_only=False,error_message=None,default_value=None,field_hidden_data=None,validators=[]):
        super().__init__(title=title,input_text=input_text,validators=validators,required=required,read_only=read_only,value_from_callback=True,error_message=error_message,default_value=default_value,field_hidden_data=field_hidden_data)

    def create_variables_keys(self):
        keyboard = types.InlineKeyboardMarkup()
        t_id = self._append_variable_data(True)
        f_id = self._append_variable_data(False)
        keyboard.add(types.InlineKeyboardButton(text=self.true_icon, callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format(t_id)),types.InlineKeyboardButton(text=self.false_icon, callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format(f_id)))
        return keyboard

    def message_text_data_format(self):
        if self.value == None:
            return self.value
        if self.value:
            return self.true_icon
        return self.false_icon

    def replace_field_icon(self):
        if self.value == None:
            return
        if self.value:
            return self.true_icon
        return self.false_icon



class ChooseField(Field):
    selected_icon = "✅"
    back_button_text = "🔙"
    def __init__(self,title=None,input_text=None,answer_list=[],multiple=False,required=True,read_only=False,error_message=None,pagination_after=50,button_in_row=8,field_hidden_data=None,answer_mapping=None,validators=[]):
        self.answer_list = answer_list
        self.multiple = multiple
        self.answer_mapping = answer_mapping
        self._offset = 0
        self.button_in_row = button_in_row
        self.pagination_after = pagination_after
        super().__init__(title=title,input_text=input_text,validators=validators,required=required,read_only=read_only,value_from_callback=True,error_message=error_message,field_hidden_data=field_hidden_data)
        self.value_from_callback_manual_mode = True
        if self.multiple:
            self.without_system_key = True

    def format_return_value(self,upd):
        if not self.answer_mapping:
            return upd
        if upd not in list(self.answer_mapping.keys()):
            return upd
        return self.answer_mapping[upd]


    def create_variables_keys(self):
        keyboard = types.InlineKeyboardMarkup()
        key_list = []
        iter_list = self.answer_list
        if len(self.answer_list) > self.pagination_after:
            if self._offset == 0:
                iter_list = self.answer_list[:self.pagination_after]
            else:
                iter_list = self.answer_list[(self._offset * self.pagination_after):][:self.pagination_after]
        for i in iter_list:
            v_id = self._append_variable_data(i)
            s_icon = ""
            if self.value != None:
                if i in self.value:
                    s_icon = self.selected_icon
            text = "{}{}".format(i,s_icon)
            key = types.InlineKeyboardButton(text=text, callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format(v_id))
            key_list.append(key)
        for row in split_list(key_list,self.button_in_row):
            keyboard.row(*row)
        if len(self.answer_list) > self.pagination_after:
            if len(self.answer_list[((self._offset + 1) * self.pagination_after):]) != 0:
                keyboard.row(*[types.InlineKeyboardButton(text="➡️", callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format("next_page"))])
            if self._offset != 0:
                keyboard.row(*[types.InlineKeyboardButton(text="⬅️", callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format("back_page"))])
        if self.multiple:
            keyboard.row(types.InlineKeyboardButton(text=self.back_button_text, callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format("save_field")))
        return keyboard


    def manualy_handle_callback(self, tbf, call, form):
        new_value_id = call.data.split(":")[2]
        if str(new_value_id) == "save_field":
            event = FormEvent("field_input", sub_event_type="callback", event_data=self)
            form.event_listener(event, form.create_update_form_object(action="event_callback"))
            tbf.bot.delete_message(call.message.chat.id,call.message.message_id)
            self._offset = 0
            return tbf.send_form(call.from_user.id,form,need_init=False)
        elif str(new_value_id) == "next_page":
            if len(self.answer_list[((self._offset + 1) * self.pagination_after):]) != 0:
                self._offset += 1
        elif str(new_value_id) == "back_page":
            if self._offset != 0:
                self._offset -= 1
        else:
            new_value = self.get_variable_data(new_value_id)
            if not self.multiple:
                self.value = self.format_return_value(new_value)
                event = FormEvent("field_input",sub_event_type="callback",event_data=self)
                form.event_listener(event,form.create_update_form_object(action="event_callback"))
                tbf.bot.delete_message(call.message.chat.id,call.message.message_id)
                return tbf.send_form(call.from_user.id,form,need_init=False)
            if self.value == None:
                self.value = [self.format_return_value(new_value)]
            else:
                if self.format_return_value(new_value) in self.value:
                    ind = self.value.index(self.format_return_value(new_value))
                    del self.value[ind]
                else:
                    self.value.append(self.format_return_value(new_value))
        new_keyboard =  self.create_variables_keys()
        if not self.multiple:
            settings = tbf._get_form_settings(form,prepare_update=call.message.chat.id)
            cancel_key = types.InlineKeyboardButton(text=settings["CANCEL_BUTTON_TEXT"], callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format("save_field"))
            new_keyboard.row(cancel_key)
        tbf.fsm.set_state(call.from_user.id,FSM_GET_FIELD_VALUE, form=form._form_dumps(),field_id=self._id)
        msg = tbf.bot.edit_message_reply_markup(chat_id=call.message.chat.id,message_id=call.message.message_id,reply_markup=new_keyboard)
        return msg

    def message_text_data_format(self):
        if self.value == None:
            return ""
        if self.multiple:
            return ",".join(self.value)
        return str(self.value)




class ListField(Field):
    def __init__(self,title=None,input_text=None,save_button_text="Save({}) 💾",validators=[],required=True,read_only=False,error_message=None,min_len=1,max_len=None,default_value=None,field_hidden_data=None):
        all_validators = []
        for validator in validators:
            all_validators.append(validator)
        super().__init__(title=title,input_text=input_text,validators=all_validators,required=required,read_only=read_only,error_message=error_message,default_value=default_value,field_hidden_data=field_hidden_data)
        self.save_button_text = save_button_text        
        self.value_from_message_manual_mode = True
        self.value_from_callback_manual_mode = True
        self.min_len = min_len
        self.max_len = max_len

    def format_return_value(self,upd):
        return upd.text

    def before_input_update(self,tbf,form,update):
        self.value = None

    def manualy_handle_callback(self,tbf,call,form):
        new_value_id = call.data.split(":")[2]
        settings = tbf._get_form_settings(form,prepare_update=call.from_user.id)
        
        if str(new_value_id) == "save_field":
            event = FormEvent("field_input",sub_event_type="msg",event_data=self)
            form.event_listener(event,form.create_update_form_object(action="event_callback"))
            return tbf.send_form(call.message.chat.id,form,need_init=False)
        
        elif str(new_value_id) == "cancel_field":
            self.value = None
            idle_state = "{}:{}".format(FSM_FORM_IDE,form._form_id)
            tbf.fsm.set_state(int(call.from_user.id),idle_state,form=form._form_dumps())
            tbf.bot.delete_message(call.message.chat.id,call.message.message_id)
            return tbf.send_form(call.from_user.id,form,need_init=False)

    def manualy_handle_message(self,tbf,message,form):
        new_value = message.text
        settings = tbf._get_form_settings(form,prepare_update=message.chat.id)
        valid = True
        if not self.validate(message):
            valid = False
        else:
            if not self.value or not isinstance(self.value,list):
                self.value = []
            self.value.append(self.format_return_value(message))
            if not (self.max_len and len(self.value) == self.max_len):
                new_keyboard =  keyboard = types.InlineKeyboardMarkup()
                if len(self.value) >= self.min_len:
                    new_keyboard.row(types.InlineKeyboardButton(text=str(self.save_button_text).format(len(self.value)), callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format("save_field"))) 
                else:
                    new_keyboard.row(types.InlineKeyboardButton(text=settings["CANCEL_BUTTON_TEXT"], callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format("cancel_field"))) 
                tbf.fsm.set_state(message.from_user.id,FSM_GET_FIELD_VALUE, form=form._form_dumps(),field_id=self._id)
                msg = tbf.bot.send_message(message.chat.id,self.input_text,reply_markup=new_keyboard)
                return msg
        event = FormEvent("field_input",sub_event_type="msg",event_data=self)
        if not valid:
            event.event_type = "field_input_invalid"
        form.event_listener(event,form.create_update_form_object(action="event_callback"))
        msg = tbf.send_form(message.from_user.id,form,need_init=False)
        if not valid:
            error_text = settings["INVALID_INPUT_TEXT"]
            if field.error_message:
                error_text = field.error_message
            elif form.form_global_error_message:
                error_text = form.form_global_error_message
            self.bot.reply_to(message,error_text)


class DateTimeField(Field):
    BACK_BUTTON_TEXT = "🔙"
    HOURS_ICON_TEXT = "🕐"
    FORM_ICON = "📅"

    EN_MONTH_NAMES: List[str] = [
        'January', 'February', 'March',
        'April', 'May', 'June', 'July', 
        'August', 'September', 
        'October', 'November', 'December'
    ]
    UA_MONTH_NAMES: List[str] = [
        'Січень', 'Лютий', 'Березень', 
        'Квітень', 'Травень', 'Червень',
        'Липень', 'Серпень', 'Вересень',
        'Жовтень', 'Листопад', 'Грудень'
    ]
    RU_MONTH_NAMES: List[str] = [
        'Январь', 'Февраль', 'Март',
        'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь',
        'Октябрь', 'Ноябрь', 'Декабрь'
    ]

    @classmethod
    def get_last_month_day(cls, from_year: int = None, from_month: int = None):
        today = datetime.today()
        last_day_date = datetime(
            from_year if from_year is not None else today.year,
            today.month if from_month is None else from_month, 1) + timedelta(days=32 - today.day)
        last_day_date = last_day_date.replace(day=1) - timedelta(days=1)
        return int(last_day_date.date().day)
    
    @classmethod
    def days_in_month(cls, year: int, month: int):
        if month == 2:
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                return 29
            else:
                return 28
        elif month in [4, 6, 9, 11]:
            return 30
        else:
            return 31

    def __init__(
                self, title=None, input_text=None,
                validators=[], required=True, read_only=False, error_message=None,
                default_value: Optional[datetime] = None, field_hidden_data=None,
                only_time: Optional[bool] = False, only_date: Optional[bool] = False,
                custom_month_names: Optional[List[str]] = None,
                years_range: Optional[int] = 20, current_year_only: Optional[bool] = True,
                seconds_input: bool = False,
                month_names_lang_code: Optional[str] = "EN",
                custom_hours_icon_text: Optional[str] = None):
        if month_names_lang_code not in ["EN", "RU", "UA"]:
            raise AttributeError('month_names_lang_code not in ["EN", "RU", "UA"]')
        self.years_range = years_range
        self.hours_icon_text = custom_hours_icon_text if custom_hours_icon_text is not None else self.HOURS_ICON_TEXT
        self.current_year_only = current_year_only
        self.only_time = only_time
        self.only_date = only_date
        self.seconds_input = seconds_input
        month_list = getattr(self, "{}_MONTH_NAMES".format(month_names_lang_code))
        if custom_month_names is not None:
            if len(custom_month_names) != 12:
                raise IndexError("custom_month_names len != 12")
            month_list = custom_month_names
        self.month_list = month_list
        all_validators = []
        for validator in validators:
            all_validators.append(validator)
        super().__init__(
            title=title, input_text=input_text, validators=all_validators,
            required=required, read_only=read_only, error_message=error_message,
            default_value=default_value,field_hidden_data=field_hidden_data, value_from_callback=True)
        self.value_from_callback_manual_mode = True
        self.without_system_key = True

    def format_return_value(self, upd):
        new_value_id = str(upd.data).split(":")[2]
        new_value = self.get_variable_data(new_value_id)
        if len(self.value) == 0:
            new_value = int(new_value)
        elif len(self.value) == 1:
            new_value = int(self.month_list.index(new_value)) + 1
        elif len(self.value) == 2 or len(self.value) == 3:
            new_value = int(''.join(filter(str.isdigit, str(new_value))))
        elif len(self.value) == 4 or len(self.value) == 5:
            new_value = int(str(new_value).split(":")[-1])
        self.value.append(new_value)
        if len(self.value) == 3 and self.only_date is True:
            self.value.extend([None, None])
            if self.seconds_input is True:
                self.value.append(None)
        
        if (len(self.value) == 5 and self.seconds_input is False) or (len(self.value) == 6 and self.seconds_input):
            if self.only_date:
                return date(year=self.value[0], month=self.value[1], day=self.value[2])
            elif self.only_time:
                return time(
                    hour=self.value[3], minute=self.value[4], second=self.value[5] if self.seconds_input else None)
            else:
                return datetime(
                    year=self.value[0], month=self.value[1],
                    day=self.value[2], hour=self.value[3], minute=self.value[4])

    def create_variables_keys(self, cancel_but: bool = True):
        keyboard = types.InlineKeyboardMarkup()
        key_list = []
        select_list = []
        row_size = 4
        if not isinstance(self.value, list):
            self.value = []
        if len(self.value) == 0 and self.only_time is False and self.current_year_only is True:
            self.value = [int(datetime.now().year)]
        elif len(self.value) == 0 and self.only_time is True:
            self.value = [None, None, None]
        
        if len(self.value) == 3:
            select_list = ["{}: {}".format(str(i), self.hours_icon_text) for i in range(1, 24)]
            select_list.append("00: {}".format(self.hours_icon_text))
        elif len(self.value) == 4:
            row_size = 6
            select_list.append("{}:00".format(self.value[3]))
            select_list = ["{}:{}".format(self.value[3], str(i) if i >= 10 else f"0{i}" ) for i in range(1, 60)]
        elif len(self.value) == 5 and self.seconds_input is True:
            row_size = 5
            select_list.append("{}:{}:00".format(self.value[3], self.value[4]))
            select_list.extend(["{}:{}:{}".format(
                self.value[3], self.value[4], str(i) if i >= 10 else f"0{i}" ) for i in range(1, 60)])
        
        elif len(self.value) == 0:
            select_list.append(int(datetime.now().year))
            for i in range(1, int(self.years_range) + 1):
                select_list.append(int(select_list[-1]) - 1)
        elif len(self.value) == 1:
            select_list = list(self.month_list)
            row_size = 3
        elif len(self.value) == 2:
            m_name = self.month_list[int(self.value[1]) - 1]
            last_month_day = self.days_in_month(int(self.value[0]), int(self.value[1]))
            select_list = ["{} {}".format(m_name, str(i)) for i in range(1, last_month_day + 1)]

        for i in select_list:
            v_id = self._append_variable_data(i)
            key = types.InlineKeyboardButton(text=i, callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format(v_id))
            key_list.append(key)
        for row in split_list(key_list, row_size):
            keyboard.row(*row)
        if cancel_but is True:
            keyboard.row(*[types.InlineKeyboardButton(
                text=self.BACK_BUTTON_TEXT, callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format("back_to"))])
        return keyboard

    def manualy_handle_callback(self,tbf,call,form):
        if str(call.data).split(":")[2] == "back_to":
            tbf.bot.delete_message(call.message.chat.id,call.message.message_id)
            self.value = None
            return tbf.send_form(call.from_user.id,form,need_init=False)
        done_value = self.format_return_value(call)
        if done_value is not None:
            self.value = done_value
            event = FormEvent("field_input", sub_event_type="callback", event_data=self)
            form.event_listener(event, form.create_update_form_object(action="event_callback"))
            tbf.bot.delete_message(call.message.chat.id, call.message.message_id)
            return tbf.send_form(call.from_user.id, form, need_init=False)

        new_keyboard =  self.create_variables_keys(cancel_but=False)
        settings = tbf._get_form_settings(form,prepare_update=call.message.chat.id)
        cancel_key = types.InlineKeyboardButton(text=settings["BACK_TEXT"], callback_data=DEFAULT_VALUE_FROM_CALLBACK_PATTERN.format("back_to"))
        new_keyboard.row(cancel_key)
        tbf.fsm.set_state(call.from_user.id,FSM_GET_FIELD_VALUE, form=form._form_dumps(),field_id=self._id)
        msg = tbf.bot.edit_message_reply_markup(chat_id=call.message.chat.id,message_id=call.message.message_id,reply_markup=new_keyboard)
        return msg

    def message_text_data_format(self):
        if not isinstance(self.value, (datetime, date, time)):
            return
        if self.only_date:
            return self.value.strftime("%Y.%m.%d")
        elif self.only_time:
            return self.value.strftime("%H:%M:%S")
        return self.value.strftime("%Y.%m.%d %H:%M:%S")

    def replace_field_icon(self):
        if not isinstance(self.value, (datetime, date, time)):
            return
        return str(self.FORM_ICON)