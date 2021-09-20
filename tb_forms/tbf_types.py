

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
