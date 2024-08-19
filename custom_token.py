
INDENT = "  "

class Token:
    def __init__(self, name: str, content: str = ""):
        self.name       = name
        self.content    = content
    
    def isempty(self):
        if self.content == "\n":
            return True
        if self.content.startswith(" "):
            return True
        return False

    def __str__(self) -> str:
        if not self.isempty():
            return f"{self.name}[{self.content}]"
        return self.name
    
    def to_string(self, indent_levels: int) -> str:
        return f"{INDENT*indent_levels}{str(self)}"
    
    def __repr__(self) -> str:
        return str(self)