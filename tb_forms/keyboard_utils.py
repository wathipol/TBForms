from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def merge_keyboards_data(keyboards):
    data = []
    for keyboard in keyboards:
        if keyboard is None:
            continue
        if not isinstance(keyboard, InlineKeyboardMarkup):
            type_error_message = \
                "Keyboard element cannot be %s. Only InlineKeyboardMarkup allowed." \
                % type(keyboard)
            raise TypeError(type_error_message)
        data.extend(keyboard.keyboard)
    return data


def keyboa_combiner(keyboards = None) -> InlineKeyboardMarkup:
    """ combines multiple InlineKeyboardMarkup objects into one.
    """
    if keyboards is None:
        return InlineKeyboardMarkup()
    if isinstance(keyboards, InlineKeyboardMarkup):
        keyboards = (keyboards, )
    data = merge_keyboards_data(keyboards)
    return keyboa_maker(data)
