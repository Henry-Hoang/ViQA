from qatask.reader.T5reader.FiD import FiDT5
from qatask.reader.T5reader.data import *
from .base import BaseReader
import transformers 
from torch.utils.data import DataLoader, SequentialSampler
from tqdm import tqdm
import re

class T5multidocreader(BaseReader):
    def __init__(self, cfg=None, tokenizer=None, db_path=None) -> None:
        super().__init__(cfg, tokenizer, db_path)
        self.cfg = cfg
        self.model = FiDT5.from_pretrained(self.cfg.model_checkpoint)
        self.tokenizer = transformers.T5Tokenizer.from_pretrained("VietAI/vit5-base")
    def clean_ctx(self, ctx):
        pattern = re.compile(r'\(|\)|\[|\]|\"|\'|\{|\}|\?|\!|\;|\=|\+|\*|\%|\$|\#|\@|\^|\&|\~|\`|\|')
        ctx = pattern.sub('', ctx)
        ctx = ctx.replace('_', ' ')
        ctx = ctx.replace("-", " đến ")
        ctx = ctx.replace(":", " là ")
        ctx = ctx.replace("=", " bằng ")
        ctx = ctx.replace("\/", " ")
        return ctx

    def __call__(self, data):
        _data = []
        data_passage_scores = []
        for item in data:
            question = item['question']
            passage_scores = [passage[2] for passage in item['candidate_passages']]
            contexts_text = [self.clean_ctx(passage[3]) for passage in item['candidate_passages']]
            titles = [" " for passage in item['candidate_passages']]
            contexts = [{'text': text, 'title': title, 'score': score} for score,text,title
                 in zip(passage_scores, contexts_text, titles)]
            _data.append({'question': question, 'ctxs': contexts})
            augmented_passage_scores = passage_scores.copy()
            data_passage_scores.append(augmented_passage_scores)
        print("Reading candidate passages ...")
        #6 contexts only
        dataset = Dataset(_data, 6)
        sampler = SequentialSampler(dataset)
        #Context max length 252, max ans length 52
        collator = Collator(252, self.tokenizer, 50)
        dataloader = DataLoader(dataset,
            sampler=sampler,
            batch_size=10,
            drop_last=False,
            num_workers=10,
            collate_fn=collator
        )
        lst_ans = []
        for i, batch in tqdm(enumerate(dataloader)):
            batch_ans = []
            (idx, _, _, context_ids, context_mask) = batch

            outputs = self.model.generate(
                input_ids=context_ids.cuda(),
                attention_mask=context_mask.cuda(),
                max_length=50
            )

            for k, o in enumerate(outputs):
                ans = self.tokenizer.decode(o, skip_special_tokens=True)[0]
                batch_ans.append(ans)           
            lst_ans.extend(batch_ans)
        saved_format = {'data': []}
      # ====================== Saving logs ===================
        saved_logs = {'data': []}
        for idx, item in enumerate(lst_ans):
            # Currently we are selecting answer with max score
            # TODO: Select answer with max score and max score of retrieved passage
            item['passage_scores'] = data_passage_scores[idx]
            saved_format['data'].append({'id':'testa_{}'.format(idx+1),
                                            'question': data[idx]['question'],
                                            # 'answer': bestans,
                                            'answer': item,
            })
            if getattr(self.cfg, 'logpth') is not None:
                saved_logs['data'].append({'id':'testa_{}'.format(idx+1),
                                            'question':data[idx]["question"],
                                            'answer': item})
        if getattr(self.cfg, 'logpth') is not None:
            self.logging(saved_logs)
        print("reading done")
        return saved_format

if __name__ == "__main__":
    class Config:
        def __init__(self) -> None:
            self.model_checkpoint = "nguyenvulebinh/vi-mrc-large"
            self.batch_size = 4
    config = Config()