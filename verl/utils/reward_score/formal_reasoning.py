import re


class Task:

    def __init__(self, sub, obj, copula, freq, conf, prio, dura, qul, eb):
        # statement
        self.sub = sub
        self.obj = obj
        self.copula = copula

        # truth
        self.freq = freq
        self.conf = conf

        # budget
        self.prio = prio
        self.dura = dura
        self.qul = qul

        # properties
        self.is_question = True if freq is None else False
        self.is_judgment = False if freq is None else True

        # evidential_base
        self.eb = eb

    def decay(self):
        self.prio = max(self.prio * self.dura, self.qul)

    def string(self, show_budget=False):
        if not show_budget:
            return f"<{self.sub}{self.copula}{self.obj}>. ${self.freq}, {self.conf}$ {self.eb}"
        else:
            return (f"%{self.prio}, {self.dura}, {self.qul}% <{self.sub}{self.copula}{self.obj}>. ${self.freq}, "
                    f"{self.conf}$ {self.eb}")

    def to_json(self):
        return {"subject": self.sub,
                "object": self.obj,
                "copula": self.copula,
                "frequency": self.freq,
                "confidence": self.conf,
                "evidential_base": sorted(list(self.eb))}


def reasoning(task_1: Task, task_2: Task):
    ret = []

    if task_1.copula == task_2.copula == "-->" and len(
            {task_1.sub, task_1.obj, task_2.sub, task_2.obj}) == 3 and not task_1.eb.intersection(task_2.eb):
        copula = task_1.copula
        eb = task_1.eb.union(task_2.eb)

        # forward reasoning
        if task_1.is_judgment and task_2.is_judgment:

            if task_1.sub == task_2.sub:
                # induction
                # A -> B, A -> C
                # --------------
                # B -> C, C -> B
                ret.append(Task(task_1.obj, task_2.obj, copula,
                                task_1.freq * task_2.freq * task_1.conf * task_2.freq,
                                task_2.freq * task_1.conf * task_2.conf,
                                (task_1.prio + task_2.prio) / 2,
                                task_2.dura, task_2.qul, eb))
                ret.append(Task(task_2.obj, task_1.obj, copula,
                                task_1.freq * task_2.freq * task_1.conf * task_2.freq,
                                task_1.freq * task_1.conf * task_2.conf,
                                (task_1.prio + task_2.prio) / 2,
                                task_1.dura, task_1.qul, eb))
                task_1.decay()
                task_2.decay()
            elif task_1.sub == task_2.obj:
                # deduction
                # A -> B, C -> A
                # --------------
                # C -> B
                ret.append(Task(task_2.sub, task_1.obj, copula,
                                task_1.freq * task_2.freq,
                                task_1.freq * task_2.freq * task_1.conf * task_2.conf,
                                (task_1.prio + task_2.prio) / 2,
                                task_2.dura, task_2.qul, eb))
                task_1.decay()
                task_2.decay()
            elif task_1.obj == task_2.sub:
                # deduction
                # A -> B, B -> C
                # --------------
                # A -> C
                ret.append(Task(task_1.sub, task_2.obj, copula,
                                task_1.freq * task_2.freq,
                                task_1.freq * task_2.freq * task_1.conf * task_2.conf,
                                (task_1.prio + task_2.prio) / 2,
                                task_1.dura, task_1.qul, eb))
                task_1.decay()
                task_2.decay()
            elif task_1.obj == task_2.obj:
                # abduction
                # A -> B, C -> B
                # --------------
                # A -> C, C -> A
                ret.append(Task(task_1.sub, task_2.sub, copula,
                                task_1.freq * task_2.freq * task_1.conf * task_2.freq,
                                task_1.freq * task_1.conf * task_2.conf,
                                (task_1.prio + task_2.prio) / 2,
                                task_1.dura, task_1.qul, eb))
                ret.append(Task(task_2.sub, task_1.sub, copula,
                                task_1.freq * task_2.freq * task_1.conf * task_2.freq,
                                task_2.freq * task_1.conf * task_2.conf,
                                (task_1.prio + task_2.prio) / 2,
                                task_2.dura, task_2.qul, eb))
                task_1.decay()
                task_2.decay()

    ret.append(task_1)
    ret.append(task_2)

    return ret


regex1 = r"(?s)task1:\s*(?P<task1>.*?)\s*task2:\s*(?P<task2>.*?)\s*results:\s*(?P<results>.*?)(?=task1:|$)"
regex2 = (r"<(?P<source>ID\d+)\s*-->\s*(?P<target>ID\d+)[^>]*>\.\$(?P<num1>\d+(?:\.\d+)?),\s*(?P<num2>\d+("
          r"?:\.\d+)?)\$\{(?P<numbers>(?:\d+(?:,\s*)?)+)\}")


def compute_score(solution_str, ground_truth):
    # currently, the ground truth is not used

    try:
        reasoning_steps = re.findall(regex1, solution_str)
    except:
        return 0.

    rs = []
    for task1, task2, results in reasoning_steps:
        r = 0.
        try:
            sub, obj, freq, conf, eb = re.findall(regex2, task1)[0]
        except:
            return 0.
        task1 = Task(sub, obj, "-->", float(freq), float(conf), 0.9, 0.5, 0.1,
                     {int(each_eb) for each_eb in eb.split(",")})
        try:
            sub, obj, freq, conf, eb = re.findall(regex2, task2)[0]
        except:
            return 0.
        task2 = Task(sub, obj, "-->", float(freq), float(conf), 0.9, 0.5, 0.1,
                     {int(each_eb) for each_eb in eb.split(",")})
        ret = reasoning(task1, task2)
        try:
            tmp = re.findall(regex2, results)
        except:
            return 0.
        r += 0.5
        A, B, C = set(), set(), set()
        for i, each_tmp in enumerate(tmp):
            mark = False
            for j, each_ret in enumerate(ret):
                if each_tmp[0] == each_ret.sub and each_tmp[1] == each_ret.obj and {int(each_eb) for each_eb in
                                                                                    each_tmp[4].split(
                                                                                            ",")} == each_ret.eb:
                    r += (2 - abs(float(each_tmp[2]) - each_ret.freq) - abs(
                        float(each_tmp[3]) - each_ret.conf)) * 0.05
                    B.add((i, j))
                    mark = True
                    break
            if not mark:
                A.add(i)
        C = set(range(len(ret))) - set((each_B[1] for each_B in B))
        r -= 0.4 * len(A) + 0.4 * len(C)
        rs.append(r)

    return sum(rs) / len(rs)


if __name__ == "__main__":
    s = ("Suppose we have: ID0 is certainly a kind of ID1. ID1 is certainly a kind of ID2. The question is: whether "
         "ID0 is a kind of ID2 ? Represent the answer step by step using formal reasoning.task1:<ID0-->ID1>.$0.0,"
         "0.9${0},task2:<ID1-->ID2>.$0.75,0.9${1},results:[<ID0-->ID2>.$0.0,0.0${0,1},<ID0-->ID1>.$0.0,0.9${0},"
         "<ID1-->ID2>.$0.75,0.9${1}]")
    print(reward(s))
