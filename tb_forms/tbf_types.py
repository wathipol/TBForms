

class MediaData:
    """ Данные медиа поля """

    def __init__(self,caption,media_type,file_id,original_update):
        self.caption = caption
        self.media_type = media_type
        self.file_id = file_id
        self.original_update = original_update


    def __repr__(self):
        return "<MediaData(caption='{}', media_type='{}', file_id='{}',original_update=<Telebot Message object>)>".format( \
            self.caption,self.media_type,self.file_id
        )


class FormEvent:
    def __init__(self,event_type: str,sub_event_type = None,event_data = None):
        self.event_type = event_type
        self.sub_event_type = sub_event_type
        self.event_data = event_data

    def __repr__(self):
        return "<FormEvent(event_type='{}',sub_event_type='{}',event_data={})>".format(self.event_type,self.sub_event_type,self.event_data)
