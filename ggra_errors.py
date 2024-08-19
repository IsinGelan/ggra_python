
class GgraError(Exception):
    """GgraError if the shit hits the fan"""
    def __init__(self, origin: str, message_lines: list[str]):
        """GgraError if the shit hits the fan"""
        self.origin_obj     = origin
        self.message_lines  = message_lines
        super().__init__(message_lines)
        self.__suppress_context__ = True
    
    def __str__(self) -> str:
        content = "".join(f"    {line}\n" for line in self.message_lines)
        return f"\nGGRA: {self.origin_obj}\n{content}"

class GgraParserError(GgraError):
    pass

class GgraResolutionError(GgraError):
    pass