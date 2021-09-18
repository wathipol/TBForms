from . import tbf_types

all_content_types = ['text', 'audio', 'document', 'photo', 'sticker', 'video', 'video_note', 'voice', 'location', 'contact', 'new_chat_members', 'left_chat_member', 'new_chat_title', 'new_chat_photo', 'delete_chat_photo', 'group_chat_created', 'supergroup_chat_created', 'channel_chat_created', 'migrate_to_chat_id', 'migrate_from_chat_id', 'pinned_message']


class Validator:
    """ Основной класс валидатора """
    def __init__(self):
        pass

    def validate(self,test_value) -> bool:
        pass



"""

Валидатор это класс который наследует у Validator
    Должна быть переопределена функция validate, которая возвращает булевое значение статуса валидации

"""



class isNumber(Validator):
    """ Валидация ввода только чисел """
    def __init__(self,only_int=False,min_num=None,max_num=None):
        self.only_int = only_int
        self.min_num = min_num
        self.max_num = max_num


    def validate(self,upd):
        test_value = upd.text
        if isinstance(test_value,(int,float)):
            if self.only_int:
                if instance(test_value,float):
                    return False
            if self.min_num:
                if test_value < self.min_num:
                    return False
            if self.max_num:
                if test_value > self.max_num:
                    return False
            return True
        else:
            try:
                to_float = float(test_value)
                if self.only_int:
                    if not to_float.is_integer():
                        return False
                if self.min_num:
                    if to_float < self.min_num:
                        return False
                if self.max_num:
                    if to_float > self.max_num:
                        return False
                return True
            except Exception as e:
                return False
            return False



class isMedia(Validator):
    """ Валидация только медиа сообщений """
    def __init__(self,valid_types=[],caption_required=False,only_text_aviable=False):
        self.valid_types = valid_types
        self.caption_required = caption_required
        self.only_text_aviable = only_text_aviable

    def get_media_data(self,upd):
        msg_type = str(upd.content_type)
        if msg_type == "text" and self.only_text_aviable:
            return tbf_types.MediaData(upd.text,msg_type,None,upd)


        media_data = {
            "caption":upd.caption,
            "media_type":msg_type,
            "file_id":None,
            "original_update":upd
        }

        if msg_type == "document":
            media_data["file_id"] =  str(upd.document.file_id)
        elif msg_type == "video":
            media_data["file_id"] = str(upd.video.file_id)
        elif msg_type == "photo":
            media_data["file_id"] = str(upd.photo[-1].file_id)
        return tbf_types.MediaData(**media_data)


    def validate(self,upd):
        msg_type = str(upd.content_type)
        if msg_type == "text":
            if self.only_text_aviable:
                return True
            return False
        if self.valid_types:
            if msg_type not in self.valid_types:
                return False
        if not upd.caption and self.caption_required:
            return False
        return True


class StringValidator(Validator):
    """ Валидация для строк """
    _only_latin_list = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z','A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
    _num_list = ["0","1","2","3","4","5","6","7","8","9"]

    def __init__(self,only_latin=False,white_list=[],black_list=[],min_len=None,max_len=None,block_number=False,only_white_list=False):
        self.only_latin = only_latin
        self.white_list = white_list
        self.black_list = black_list
        self.min_len = min_len
        self.max_len = max_len
        self.block_number = block_number
        self.only_white_list = only_white_list


    def validate(self,message):
        if not message.text:
            return False
        if self.min_len:
            if len(str(message.text)) < self.min_len:
                return False
        if self.max_len:
            if len(str(message.text)) > self.max_len:
                return False
        for lit in message.text:
            if self.only_white_list:
                if lit not in self.white_list:
                    return False
            elif self.only_latin:
                if lit in self._only_latin_list:
                    if lit not in self.black_list:
                        continue
                elif lit in self._num_list:
                    if not self.block_number:
                        continue
                elif lit in self.white_list:
                    continue
                else:
                    return False
            else:
                if self.block_number and lit in self._num_list:
                    return False
                if lit in self.black_list:
                    return False
        return True
