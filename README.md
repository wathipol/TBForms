# TelebotForms
Small extension for [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) library for building interactive forms in Telegram bots.

## Install
```
$ pip install TbfForms
```
## Example build simple form
```python
from tb_forms import TelebotForms,BaseForm,fields
from telebot import TeleBot

bot = TeleBot("your_token")
tbf = TelebotForms(bot)

class TestRegisterForm(BaseForm):
    update_name = "submit_register_form"
    form_title = "TBF Test Register Form"
    name = fields.StrField("Name","Enter your name:")
    age = fields.NumberField("Age","Select your age:",only_int=True,key_mode=True)
    sex = fields.ChooseField("Sex","Select your sex:",answer_list=["male","female"])
    photo = fields.MediaField("Photo","Enter your photo:",valid_types=['photo'],required=False,error_message="Error. You can only send a photo")
    freeze_mode = True
    close_form_but = False
    submit_button_text = "Register"

@bot.message_handler(commands=['start'])
def start_update(message):
    tbf.send_form(message.chat.id,TestRegisterForm())

@tbf.form_submit_event("submit_register_form")
def submit_register_update(call,form_data):
    print(form_data) # Completed form data
    bot.send_message(call.message.chat.id,"Successful registration")

```
## Docs

### TelebotForms

#### Init

| Args  | Required? |  Default  |  Type   | Description     |
| ------------- | ------------- |------------- |------------- |------------- |
| bot  | Yes  |   | telebot.TeleBot object  |pyTelegramBotAPI bot object |
| fsm  | No  | tb_forms.ffsm.MemoryFSM | tb_forms.ffsm.FSM | TbfForms FSM object |

#### Settings 
```python
tbf = TelebotForms(bot)

# Global icon for a missing value field 
tbf.GLOBAL_MISSING_VALUE_ICON: str = "💢"

# Global icon for a field with data  
tbf.GLOBAL_EDIT_ICON: str = "✏️"

''' Global cancel form button text
  Type: Union[Str,Callable]   '''
tbf.GLOBAL_CANCEL_BUTTON_TEXT = "Cancel"
# Callable example
tbf.GLOBAL_CANCEL_BUTTON_TEXT = lambda user_id: "Cancel"



# Global submit form button text
tbf.GLOBAL_SUBMIT_BUTTON_TEXT: str = "Submit"

# Global close button in form
tbf.GLOBAL_CLOSE_FORM_BUT:bool = True

''' Global form freeze mode. 
If True, prohibits any action prior to submitting or canceling the  form. '''
tbf.GLOBAL_FREEZE_MODE:bool = True

''' Global freeze mode alart text. 
If freeze_mode is True, sends this text after any action. 
  Type: Union[Str,Callable]   '''
tbf.GLOBAL_STOP_FREEZE_TEXT = "Cancel or submit the form first before proceeding further"

''' Global invalide input error text.  
  Type: Union[Str,Callable]   '''
tbf.GLOBAL_INVALID_INPUT_TEXT = "Error. Invalide input!"

```

#### Methods

* send_form - Send form to chat

| Args  | Required? |  Default  |  Type   | Description     |
| ------------- | ------------- |------------- |------------- |------------- |
| chat_id  | Yes  |   | int  |Chat id for send form |
| form  | Yes  |  | tb_forms.BaseForm | TbfForms Form object |

* form_submit_event - handle submit form event

| Args  | Required? |  Default  |  Type   | Description     |
| ------------- | ------------- |------------- |------------- |------------- |
| update_name | Yes  |   | str  |update_name of form to handle |
```python
@tbf.form_submit_event("update_name")
def submit_update(call,form_data):
    pass
```
* form_cancel_event - handle cancel form event

| Args  | Required? |  Default  |  Type   | Description     |
| ------------- | ------------- |------------- |------------- |------------- |
| update_name | Yes  |   | str  |update_name of form to handle |
```python
@tbf.form_cancel_event("update_name")
def cancel_form_update(call,form_data):
    pass

```
* form_event - handle all form event

| Args  | Required? |  Default  |  Type   | Description     |
| ------------- | ------------- |------------- |------------- |------------- |
| update_name | Yes  |   | str  |update_name of form to handle |
| action | Yes  |   | list  | handle events type |
```python
@tbf.form_event("update_name",action=["submit","cancel"])
def form_event_update(call,form_data):
    print(form_data.update_action)
```



