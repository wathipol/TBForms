from collections import namedtuple
import time
import pickle

TB_FORM_TAG = "_tbf"
DEFAULT_CANCEl_CALLBACK = "{}:default_cancel".format(TB_FORM_TAG)
DEFAULT_CANCEl_FORM_CALLBACK = "{}:default_cancel_form".format(TB_FORM_TAG)

DEFAULT_SUBMIT_CALLBACK = "{}:submit_form".format(TB_FORM_TAG)
DEFAULT_VALUE_FROM_CALLBACK_PATTERN = "{}:call_value:{}".format(TB_FORM_TAG,"{}")
FIELD_CLICK_CALLBACK_DATA_PATTERN = "{}:call:{}".format(TB_FORM_TAG,"{}")
FSM_FORM_IDE = "{}:idle_form".format(TB_FORM_TAG)
FSM_GET_FIELD_VALUE = "{}:form_get_value".format(TB_FORM_TAG)


class State:
    """ Обьект Состояния """
    def __init__(self,state,life_time=False,**args):
        self.state = state
        self.life_time = life_time
        self.args = namedtuple("Args", args.keys())(*args.values())

    def __repr__(self):
        return "<State(state={}, args={})>".format(self.state,self.args)



class FSM:
    """ Основной класс для работы FSM """
    _idle_state = "idle"

    def set_state(self,user_id: int,state: str,**args) -> None:
        """ Установить состояние для конкретного пользователя """
        pass

    def get_state(self,user_id: int) -> State:
        return State(self._idle_state)

    def reset_state(self,user_id: int) -> None:
        pass

    def check_already_form(self,user_id):
        if ":".join(str(self.get_state(user_id).state).split(":")[0:2]) == FSM_FORM_IDE:
            return True
        return False


    def check_input_status(self,user_id):
        if self.get_state(user_id).state == FSM_GET_FIELD_VALUE:
            return True
        return False


class MemoryFSM(FSM):
    """ Работа с конечными автоматами в памяти """
    _data = {}
    AUTO_CLEAR_TIMEOUT = True

    def clear_timeout(self):
        for user_id in self._data:
            fsm_data = self._data[user_id]
            if fsm_data.life_time:
                if (time.time() - fsm_data.create_time) >= fsm_data.life_time:
                    del self._data[user_id]

    def set_state(self,user_id: int,state: str,life_time = False,**args) -> None:
        self._data[user_id] = State(state,life_time=life_time,**args)
        self._data[user_id].create_time = time.time()


    def get_state(self,user_id: int) -> State:
        if self.AUTO_CLEAR_TIMEOUT:
            self.clear_timeout()

        if user_id in list(self._data.keys()):
            return self._data[user_id]
        return State(self._idle_state)

    def reset_state(self,user_id: int) -> None:
        del self._data[user_id]



class RedisFSM(FSM):
    """ FSM в базе данных Redis """
    fsm_prefix = "_fsm"
    def __init__(self,redis_client):
        self.redis_client = redis_client

    def set_state(self,user_id: int,state: str,life_time = None,**args) -> None:
        state_data = {
            "state":state,
            "args":args,
            "create_time":time.time(),
            "life_time":life_time
        }
        keyname = "{}:{}".format(self.fsm_prefix,user_id)
        if life_time:
            self.redis_client.setex(keyname,life_time,value=pickle.dumps(state_data))
        else:
            self.redis_client.set(keyname,pickle.dumps(state_data))


    def get_state(self,user_id: int) -> State:
        keyname = "{}:{}".format(self.fsm_prefix,user_id)
        state_data = self.redis_client.get(keyname)
        if not state_data:
            return State(self._idle_state)
        state_data = pickle.loads(state_data)
        return State(state_data["state"],life_time=state_data["life_time"],**state_data["args"])


    def reset_state(self,user_id: int) -> None:
        keyname = "{}:{}".format(self.fsm_prefix,user_id)
        self.redis_client.delete(keyname)
