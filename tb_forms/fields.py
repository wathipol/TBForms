import random
import string
import dill
from . import validators as fvalidators
from .validators import all_content_types,Validator
from .tbf_types import FormEvent
from telebot import types
from .tb_fsm import TB_FORM_TAG,DEFAULT_CANCEl_CALLBACK,FIELD_CLICK_CALLBACK_DATA_PATTERN,DEFAULT_VALUE_FROM_CALLBACK_PATTERN,FSM_GET_FIELD_VALUE

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
        self.without_system_key = False
        self.value = default_value
        self.variable_data = {}
        self.error_message = error_message
        self.validators = self._fix_validators_type(self.validators)
        self.field_hidden_data = field_hidden_data




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


    def manualy_handle_callback(self,tbf,call,form):
        new_value_id = call.data.split(":")[2]
        if str(new_value_id) == "save_field":
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
