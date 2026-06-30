class SigException(Exception):
    def __init__(self,code="", message="Sig default exception"):
        self.message = message
        self.code = code
        super().__init__(self.message)