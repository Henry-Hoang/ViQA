class BaseReader:
    def __init__(self, cfg, tokenizer) -> None:
        self.cfg = cfg
        self.tokenizer = tokenizer
    
    def __call__(self, data):
        return data