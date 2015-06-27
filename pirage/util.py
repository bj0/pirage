
class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        # super().__init__(*args, **kwargs)
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
