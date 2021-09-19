# TelebotForms
Small extension for [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) library for building interactive forms in Telegram bots.

## Install
```
$ pip install TbfForms
```
## Example build simple form
```python
from tb_forms import TelebotForms,ffsm,BaseForm,fields
from telebot import TeleBot

bot = TeleBot("your_token")
tbf = TelebotForms(bot)

class TestRegisterForm(BaseForm):
    update_name = "submit_register_form"
    form_title = "TBF Test Register Form"
    name = fields.StrField("Name","Enter your name:")
    age = fields.NumberField("Age","Select your age:",only_int=True,key_mode=True)
    sex = fields.ChooseField("Sex","Select your sex:",answer_list=["male","female"])
    photo = fields.MediaField("Photo","Enter your photo:",required=False,error_message="Error. You can only send a photo")
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

