from pathlib import Path
import re
import math
import os
import requests

path = Path(__file__).parent / "data" / "harness_survey.md"
text = path.read_text(encoding="utf-8")

STOP = set(
    "the a an of to in on and or for is are was were be been with as at by from "
    "this that it its we our they their can not but if then than which who what "
    "how why does do did have has had will would could should more most such "
    "other into over under about between during before after above below up down "
    "out off again further once here there when where while both each few many "
    "some any no nor only own same so very just also".split()
)

def get(text):
    chunks = []
    buf = []
    chapter = ""
    section = ""
    n1 = 0
    n2 = 0
    n = 0
    for line in text.splitlines():
        data = {"number": n ,"chapter": chapter, "section": section, "text": "\n".join(buf)}
        if line.startswith("## "):
            if buf:
                n += 1
                chunks.append(data)
                buf.clear()
            chapter = line[3:]
            section = ""
            n1 += 1
        elif line.startswith("### "):
            if buf:
                n += 1
                chunks.append(data)
                buf.clear()            
            section = line[4:]
            n2 += 1
        else:
            buf.append(line)
    if buf:
        chunks.append({"number": n ,"chapter": chapter, "section": section, "text": "\n".join(buf)})
    chunks = [c for c in chunks if c["chapter"] and c["text"].strip()]
    return chunks

def split_words(sentence):
    words = re.findall(r"[a-z]+", sentence.lower())
    clean = []
    for w in words:
        if w not in STOP:
            clean.append(w)
    return clean

def score(question, chunk, N, df):
    q = split_words(question)
    words = split_words(chunk["text"])
    section_words = split_words(chunk["section"])
    total = 0
    section_total = 0
    for w in q:
        count = words.count(w)
        if count > 0:
            total += count * math.log(N / df[w])
        section_count = section_words.count(w)
        if section_count > 0:
            section_total += section_count * math.log(N / df[w]) * 3
    return (total + section_total) / (len(words) ** 0.5)

def chat(content):
    key = os.environ.get("DEEPSEEK_API_KEY")
    base = "https://api.deepseek.com/chat/completions"

    try:
        r = requests.post(
            base,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": "deepseek-chat",
                "messages": [{"role": "system", "content": "只根据资料回答，每句后面要标注依据哪一块，格式是[数字]，数字就是块开头那个号；用和问题相同的语言回答。资料里没有找到答案的，就直接说「资料里没有找到」，不要用资料以外的知识补充。只能引用上面给出的块，不要编造块号。"},
                            {"role": "user", "content": content},
                            ],
                "temperature": 0
                },
            timeout=60
        )
        r.raise_for_status()

    except requests.exceptions.HTTPError as e:
        print(type(e))
        print(e)

    except requests.exceptions.Timeout:
        print("请求超时")

    except requests.exceptions.ConnectionError:
        print("连不上服务器")
    else:
        return r.json()["choices"][0]["message"]["content"]

def has_chinese(s):
    return re.search(r"[\u4e00-\u9fff]", s) is not None

def translate(q):
    key = os.environ.get("DEEPSEEK_API_KEY")
    r = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": "deepseek-flash",
            "messages": [
                {"role": "system", "content": "把用户的问题翻译成英文，只输出英文译文，不要解释，不要加引号"},
                {"role": "user", "content": q},
            ],
            "temperature": 0,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def pick(sd, gap=1.5, min_k=2, max_k=6, skip_first=False):
    k = max_k
    start = min_k - 1 if skip_first else 0
    for i in range(start, min(max_k, len(sd) - 1)):
        cur, nxt = sd[i][0], sd[i + 1][0]
        if nxt <= 0:
            k = i + 1
            break
        if cur / nxt >= gap:
            k = i + 1
            break
    return max(k, min_k)

def main():
    qwords = input("用户：")
    if has_chinese(qwords):
        qwords = translate(qwords)
        print(f"（翻译成英文去查：{qwords}）")
    chunks = get(text)

    df = {}
    for c in chunks:
        for w in set(split_words(c["text"] + c["section"] + c["chapter"])):
            df[w] = df.get(w, 0) + 1

    N = len(chunks)

    score_data = []
    pr = []
    for c in chunks:
        score_data.append((score(qwords, c, N, df), c))
    score_data.sort(key= lambda w: w[0], reverse=True)
    k = pick(score_data, skip_first=True)
    for p in score_data[:k]:
        pr.append(p[1])

    low = score_data[0][0] < 0.5
    flat = True
    for i in range(1, min(k, len(score_data)) - 1):
        cur = score_data[i][0]
        nxt = score_data[i + 1][0]
        if nxt <= 0 or cur / nxt >= 1.5:
            flat = False
            break
    warn = low and flat
    if warn:
        print("（预警：检索分数偏低且无断层，资料可能不足）")

    nprs = ""
    if warn:
        nprs += "（注意：这批资料与问题的相关性可能不足。如果资料里没有明确答案，就直接说「资料里没有找到」，不要用资料以外的知识补充。）\n"
    for npr in pr:
        nb = npr["number"]
        cp = npr["chapter"]
        st = npr["section"]
        tx = npr["text"]
        nprs += (f"[{nb}] {cp} {st} {tx} \n \n \n")

    print(chat(qwords + nprs))

if __name__ == "__main__":
    main()

