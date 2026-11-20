import main
from pathlib import Path
import json
import re

qs = [
    "What is the difference between the functional view and the implementation view of an agent?",
    "What are the four paradigms of agent engineering?",
    "What are the six components of the execution harness?",
    "How does the context manager decide what enters the model's context?",
    "What kinds of actions does the action interface expose?",
    "How much does the harness change performance on SWE-bench Verified?",
    "What is the difference between harness generalization and specialization?",
    "Why does the survey argue that model-centric scaling has limits?",
    "观测接口和动作接口分别管什么",
    "上下文管理器怎么决定哪些信息进入模型的上下文",
]

path = Path(__file__).parent / "data" / "harness_survey.md"
text = path.read_text(encoding="utf-8")

chunks = main.get(text)
df = {}
for c in chunks:
    for w in set(main.split_words(c["text"] + c["section"] + c["chapter"])):
        df[w] = df.get(w, 0) + 1
N = len(chunks)

with open(Path(__file__).parent / "expected.json", encoding="utf-8") as f:
    data = json.load(f)

def stem(w):
    if w.endswith("ies") and len(w) > 3:
        return w[:-3] + "y"
    if w.endswith("ing") and len(w) > 5:
        return w[:-3]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w

def hit_rate(answer, keys):
    got = {stem(w) for w in main.split_words(answer)}
    ok = 0
    for k in keys:
        parts = [stem(w) for w in main.split_words(k)]
        if parts and all(p in got for p in parts):
            ok += 1
    return ok / len(keys)

if __name__ == "__main__":
    for n, q in enumerate(qs, start=1):
        if main.has_chinese(q):
            q = main.translate(q)
            print(f"第 {n} 题（中文）译成：{q}")
        sd = [(main.score(q, c, N, df), c) for c in chunks]
        sd.sort(key=lambda x: x[0], reverse=True)
        k = main.pick(sd, skip_first=True)
        pr = [x[1] for x in sd[:k]]
        nprs = ""
        for npr in pr:
            nprs += f"[{npr['number']}] {npr['chapter']} {npr['section']} {npr['text']} \n \n \n"

        answer = main.chat(q + nprs)
        if answer is None:
            print(False)
            print("（接口没返回，这题跳过）")
            continue
        refs = [int(x[1:-1]) for x in re.findall(r"\[\d+\]", answer)]
        num = any(b in data[f"{n}"]["blocks"] for b in refs)

        hit = hit_rate(answer, data[f"{n}"]["words"])
        if hit >= 0.6 and num:
            print(True)
        else:
            print(False)
        print(answer)
        print(hit, refs, data[f"{n}"]["blocks"])
