import dill
from typing import Optional, Any
from telebot.types import Message


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


class MediaData:
    """ Данные медиа поля """

    def __init__(self, caption: Optional[str], media_type: str, file_id: str, original_update: Optional[Message] = None):
        self.caption = caption
        self.media_type = media_type
        self.file_id = file_id
        self.original_update = original_update


    def __repr__(self):
        return "<MediaData(caption='{}', media_type='{}', file_id='{}',original_update=<Telebot Message object>)>".format( \
            self.caption, self.media_type, self.file_id
        )

        
class FormEvent:
    def __init__(self, event_type: str, sub_event_type: str = None, event_data = None):
        self.event_type = event_type
        self.sub_event_type = sub_event_type
        self.event_data = event_data

    def __repr__(self):
        return "<FormEvent(event_type='{}',sub_event_type='{}',event_data={})>".format(
            self.event_type, self.sub_event_type, self.event_data)


class NestedFormData:
    def __init__(self, form_data: Any, field_id: str):
        self.form_data = form_data
        self.field_id = field_id
    
    def __repr__(self) -> str:
        return "<NestedFormData(form_data={}, field_id={})>".format(
            self.form_data, self.field_id)