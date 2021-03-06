import re, logging, time, cProfile

class Word(object):
    def __init__(self, function, name, types, inputs):
        if name == '': 
            raise ValueError("Invalid name.")
        
        self.name = name
        self.function = function
        self.types = types  
        self.inputs = inputs

class Parser(object):
    def __init__(self):
        self.S_NOP = lambda x, tok: ('w',None)
        self.S_WRD = lambda x, tok: ('w',tok)
        self.S_STR = lambda x, tok: ('s',str(tok[1:-1]))
        self.S_INT = lambda x, tok: ('i',int(tok))
        
        self.lex = re.Scanner([
            (r"[a-zA-Z_][a-zA-Z0-9_]*", self.S_WRD), 
            (r"'(?:\\.|[^'])*'?", self.S_STR), 
            (r'"(?:\\.|[^"])*"?', self.S_STR),
            (r"-?[0-9]+", self.S_INT), 
            (r"#[^\n\r]*", self.S_NOP), 
            (r".", self.S_WRD),
        ], re.M)   

    def do(self, prg):
        c,leftovers = self.lex.scan(prg)
        if leftovers: raise ValueError("Lexer fail.")
        c = c[::-1]
        logging.debug(c)
        def recurse_blocks(inp):
            s = []
            while True:
                i = c.pop()
                if i == ('w','}'):   return ("b",s)
                elif i == ('w','{'): s.append(recurse_blocks(inp))
                else:                s.append(i)
            raise ValueError("Blocks don't match.")
        code = []
        while c:
            i = c.pop()
            if i == ('w','{'):   code.append(recurse_blocks(c))
            elif i == ('w','}'): raise ValueError("Blocks don't match.")
            else:                code.append(i)
        return code
    
class FunctionProfile(object):
    def __init__(self):
        self.time = 0
        self.calls = 1
        
    def called(self):
        self.calls += 1
        
    def __repr__(self):
        return "calls:%10s\ttotal time:%.3f" % (self.calls, self.time)

class Interpreter(object):
    def __init__(self):
        self.parser = Parser()
        
        self.words = {}
        self.profile = {}
        self.stack = []
        
        self.construct_language()
        
    def exec_ast(self, c):
        def try_run(tm,ks):
            logging.debug("try_run: %s %s %s" % (tm,ks,self.stack[-2:]))
            for k in ks:
                # go through possible type set and try to match
                if len(k) <= len(self.stack):
                    t = get_types(len(k))
                    if t == k:     
                        ex_func(tm,t)
                        return True
                else:
                    raise ValueError("Stack underflow. ",self.stack)
    
        def ex_func(tm,t):
            ww = tm+t
            self.profile[ww].called()
            logging.debug("exec: %s %s stack: %s" % (tm,t,self.stack))  
            t1 = time.time() 
            sp = []
            for _ in range(self.words[tm][t].inputs): 
                sp.append(self.stack.pop())
            logging.debug("afte: %s %s stack: %s" % (tm,t,self.stack))   
            r = self.words[tm][t].function(*sp)
            if r: 
                self.stack.extend(r)
            t2 = time.time()
            self.profile[ww].time += t2-t1
            
        def get_types(i):
            return ''.join([x[0] for x in self.stack[-i:]])
        
        def do_op(op):
            if len(self.stack)>1 and self.stack[-1][1] == ':':
                # variable definition
                self.stack.pop()
                x = [self.stack[-1]]
                logging.debug(x)
                
                self.add_word(op, '', 0)(lambda: x)
                logging.debug("set: %s %s" % (op,self.stack[-1]))
            elif op in self.words:
                # found token in wordlist
                ks = self.words[op].keys()
                if ks[0]: # word has typed parameters
                    if not try_run(op,ks): 
                        # no match found, try and coerce the types to fit
                        if op in "+-|&^": # coerce only for these ops  
                            self.stack[-1],self.stack[-2] = \
                                self._coerce(self.stack[-1],self.stack[-2])
                            ex_func(op,get_types(2))
                        elif op in "*/%<>=?": # don't care about order
                            self.stack[-1],self.stack[-2] = \
                                self.stack[-2],self.stack[-1]
                            ex_func(op,get_types(2))
                        else:
                            raise ValueError("Word %s not found for types %s." 
                                             % (op,get_types(2)))
                else: # words with no types
                    ex_func(op,'')
            else:
                raise ValueError("Function not found: %s" % (i[1]))            
        
        logging.debug("exec_ast(): %s %s" % (self._quote(c)[0][1], self.stack))
        for x,i in enumerate(c):
            if i[0] == "w":
                do_op(i[1])
            else:
                logging.debug("append: %s" % repr(i))
                self.stack.append(i)
    
    def compile(self, p):
        self.exec_ast(self.parser.do(p))
        return self.stack
    
    def _new_word(self, f,n,t,inp):
        self.profile[n+t] = FunctionProfile()
        if n in self.words:
            self.words[n][t] = Word(f,n,t,inp)
        else:
            self.words[n] = {t:Word(f,n,t,inp)}
    
    def add_word(self, n, t, inp):
        def dbg(f):
            logging.debug("new word: %s %s %s" % (f,n,t))
            return f
        return lambda f: self._new_word(dbg(f),n,t,inp)
    
    def construct_language(self):        
        self.add_word('+', 'ii', 2)(lambda a,b: [('i', a[1]+b[1])])
        self.add_word('+', 'aa', 2)(lambda a,b: [('a', b[1]+a[1])])
        self.add_word('+', 'ss', 2)(lambda a,b: [('s', b[1]+a[1])])
        self.add_word('+', 'bb', 2)(lambda a,b: [('b', b[1]+[('w',' ')]+a[1])])
        
        self.add_word('-', 'ii', 2)(lambda a,b: [('i', b[1]-a[1])])
        self.add_word('-', 'aa', 2)(lambda a,b: [('a', [x for x in b[1] 
                                                        if x not in a[1]])])
        
        self.add_word('*', 'ii', 2)(lambda a,b: [('i', a[1]*b[1])])
        
        @self.add_word('*', 'bi', 2)
        def b_i_mul(a,b):
            for _ in range(a[1]):
                self.exec_ast(b[1])

        self.add_word('*', 'ai', 2)(lambda a,b: [('a', b[1]*a[1])])
        @self.add_word('*', 'as', 2)
        def a_s_mul(a,b):
            x = [self._quote([c])[0][1] for c in b[1]]
            return [('s', a[1].join(x))]
    
        @self.add_word('*', 'aa', 2)
        def a_a_mul(a,b):
            c = []
            for x in range(len(b[1])-1):
                c.extend([b[1][x]]+a[1])
            return [('a',c+[b[1][-1]])]
                
        
        self.add_word('*', 'ss', 2)(lambda a,b: [('s', a[1].join(list(b[1])))])
        self.add_word('*', 'is', 2)(lambda a,b: [('s', b[1]*a[1])])
        
        @self.add_word('*', 'ab', 2)
        def a_b_mul(a,b):
            self.stack.extend(b[1])
            for _ in range(len(b[1])-1):
                self.exec_ast(a[1])
    
        @self.add_word('/', 'ii', 2)
        def i_i_each(a,b): return [('i', b[1]/a[1])]
        
        @self.add_word('/', 'aa', 2)
        def a_a_each(a,b): 
            suba, maia = a[1], b[1]
            x,y,i = [],[],0
            while i < len(maia):
                if maia[i] == suba[0]:
                    if maia[i:i+len(suba)] == suba: 
                        i+=len(suba)
                        y.append(('a',x))
                        x = []
                        continue
                x.append(maia[i])
                i+=1
                
            if x: y.append(('a',x))  
            return [('a', y)]
        
        @self.add_word('/', 'ai', 2)
        def a_i_each(a,b): 
            return [('a', [('a',b[1][x:a[1]+x]) 
                           for x in range(0,len(b[1]),a[1])])]
        
        @self.add_word('/', 'bb', 2)
        def b_b_each(a,b): 
            x = []
            while 1:
                x.append(self.stack[-1])
                self.exec_ast(a[1])
                self.stack.append(self.stack[-1])
                self.exec_ast(b[1])
                if self.stack.pop()[1] != 1: break
            self.stack.pop()
            self.stack.append(('a',x))

        
        @self.add_word('/', 'ab', 2)
        def a_b_each(a,b): 
            return self.exec_ast([b,a]+[('w','%'),('w','~')])
        
        @self.add_word('/', 'ss', 2)
        def s_s_each(a,b): return [('a',[('s', x) for x in b[1].split(a[1])])]
    
    
        @self.add_word('%', 'ii', 2)
        def i_i_mod(a,b): return [('i', b[1]%a[1])]
        
        @self.add_word('%', 'aa', 2)
        def a_a_mod(a,b): raise ValueError("Unimplemented.")
        
        @self.add_word('%', 'ai', 2)
        def a_i_mod(a,b): return [('a', b[1][::a[1]])]
    
        @self.add_word('%', 'ab', 2)
        def a_b_mod(a,b):
            self.stack.append(('w', '['))
            for i in b[1]:
                self.exec_ast([i]+a[1])
            self.exec_ast([('w', ']')])
    
        self.add_word('?', 'ii', 2)(lambda a,b: [('i', b[1]**a[1])])
        
        @self.add_word('?', 'ia', 2)
        def i_a_poww(a,b):
            for i,j in enumerate(a[1]): 
                if b[1] == j[1]: 
                    return [('i', i)]
            return [('i', -1)]
        
        @self.add_word('?', 'ab', 2)
        def a_b_poww(a,b):
            for i in b[1]:
                self.exec_ast([i]+a[1])
                x = self.stack.pop()
                if x == ('i', 1): 
                    self.stack.append(i)
                    break
                
                
        self.add_word('<', 'ii', 2)(lambda a,b: [('i', 0 if a[1]<b[1] else 1)])
        self.add_word('<', 'ai', 2)(lambda a,b: 
                                    [('a', [i for i in b[1] if i[1]<=a[1]])])
        self.add_word('>', 'ii', 2)(lambda a,b: [('i', 0 if a[1]>b[1] else 1)])
        self.add_word('>', 'ai', 2)(lambda a,b: 
                                    [('a', [i for i in b[1] if i[1]>a[1]])])
        
        self.add_word('<', 'si', 2)(lambda a,b: [('s',b[1][a[1]:])])

        self.add_word('=', 'ii', 2)(lambda a,b: [('i', 1 if a[1]==b[1] else 0)])      
        self.add_word('=', 'ss', 2)(lambda a,b: [('i', 1 if a[1]==b[1] else 0)])
        self.add_word('=', 'ai', 2)(lambda a,b: [b[1][a[1]]] if abs(a[1])<len(b[1]) else None)
        
        self.add_word('=', 'bi', 2)(lambda a,b: [('i', ord(self._quote([b])[0][1][1:-1][a[1]]))])
 
        self.add_word('~', 'i', 1)(lambda a: [('i', ~a[1])])
        self.add_word('~', 's', 1)(lambda a: self.exec_ast(self.parser.do(a[1])))
        self.add_word('~', 'b', 1)(lambda a: self.exec_ast(a[1]))
        self.add_word('~', 'a', 1)(lambda a: a[1])
        
        self.add_word(',', 'i', 1)(lambda a: [('a', [('i', x) for x in range(a[1])])])
        self.add_word(',', 'a', 1)(lambda a: [('i', len(a[1]))])
        
        @self.add_word(',', 'ab', 2)
        def a_b_comma(a,b):
            self.stack.append(('w', '['))
            for i in b[1]:
                self.exec_ast([i]+a[1])
                if self._true(self.stack.pop()):
                    self.stack.append(i)
            self.exec_ast([('w', ']')])
        
        self.add_word(')', 'i', 1)(lambda a: [('i', a[1]+1)])
        self.add_word(')', 'a', 1)(lambda a: [('a', a[1][:-1])]+[('i', a[1][-1][1])])
        
        self.add_word('(', 'i', 1)(lambda a: [('i', a[1]-1)])
        self.add_word('(', 'a', 1)(lambda a: [('a', a[1][1:])]+[('i', a[1][0][1])])
        
        self.add_word('!', 'i', 1)(lambda a: [('i',1-a[1])])
        self.add_word('\\', '', 2)(lambda a,b: [a,b])
        self.add_word('.', '', 1)(lambda a: [a,a])
        self.add_word(';', '', 1)(lambda a: None)
        self.add_word('@', '', 3)(lambda a,b,c: [b,a,c])
        self.add_word('`', '', 1)(lambda a: self._quote([a]))
        self.add_word('[', '', 0)(lambda: [('w','[')])

        @self.add_word(']', '', 0)
        def bracke():        
            l = []
            logging.debug("%s" % self.stack)
            while len(self.stack)>0 and self.stack[-1][1] != '[': 
                l.append(self.stack.pop())
            if len(self.stack)>0 and self.stack[-1][1] == '[': 
                self.stack.pop()
            logging.debug("bracke: %s" % l)
            self.stack.append(('a', l[::-1]))  
        
        @self.add_word('p', '', 1)
        def pputs(a): print self._quote(a[1])[0][1]
        
        self.add_word(' ', '', 0)(lambda: None)
        self.add_word(':', '', 0)(lambda: [('w',':')])
    
        @self.add_word('do', 'b', 1)
        def b_doo(a): 
            while True:
                self.exec_ast(a[1])
                if not self._true(self.stack.pop()): break

        self.add_word('$', 'i', 1)(lambda a: [self.stack[-(a[1]+1)]])
        self.add_word('$', 'a', 1)(lambda a: [('a', sorted(a[1]))])
        self.add_word('$', 's', 1)(lambda a: [('s', sorted(list(a[1])))])
        self.add_word('$', 'ab', 2)(lambda a,b: [a])
        
        self.add_word('if', '', 3)(lambda a,b,c: [b] if self._true(c) else [a])
        self.add_word('abs','i', 1)(lambda a: [('i', abs(a[1]))])
        @self.add_word('zip','a',1)
        def a_zip(i):
            a = i[1]
            artype =  a[0][0]
            l2 = len(a[0][1])
            l1 = len(a)
            b = []
            for x in range(l2):
                if artype == 'a': b.append([('a',[])])
                else: b.append([('s',"")])
                for y in range(l1):
                    if artype == 'a': b[x][0] = ('a', b[x][0][1]+[a[y][1][x]])
                    else: b[x][0] = ('s', b[x][0][1]+a[y][1][x])
            return [('a', [j[0] for j in b])]
                    
    # 0 [] "" {} = false, everything else = true
    
    def _false(self, a):
        return a == ('i', 0) or a == ('a', []) or \
               a == ('s', '') or a == ('b', [])
    
    def _true(self, a):
        return not self._false(a)
    
    def _quote(self, a):
        logging.debug("quote:"+repr(a))
        def ss(i): return '\\"' if i == '"' else i # escape inner string
        def ww(i):
            #logging.debug("  ww:"+repr(i))
            if i[0] == 'i': return "%d" % i[1]
            if i[0] == 's': return '"' + ''.join(ss(t) for t in i[1]) + '"'
            if i[0] == 'w': return i[1]
            if i[0] == 'a': return "[" + ' '.join([ww(x) for x in i[1]]) + "]"
            if i[0] == 'b': return '{' + ''.join([ww(x) for x in i[1]]) + '}'
        return [('s', ' '.join([ww(x) for x in a]))]

    def _coerce(self,a,b):
        def _raise(a):
            if a[0] == 'i': return ('a', [a])
            if a[0] == 'a': return ('s', ' '.join([repr(x[1]) for x in a[1]]))
            if a[0] == 's': return ('b', [('w',a[1])])
        
        order = {'i':0, 'a':1, 's':2, 'b':3}
        logging.debug("coerce: %s %s" % (a,b))
        while a[0] != b[0]:
            if order[a[0]] > order[b[0]]:   b = _raise(b)
            elif order[b[0]] > order[a[0]]: a = _raise(a)
        
        return a,b
 
def run_tests():
    tests = [('5~','-6'),
        ('"1 2+"~','3'),
        ('{1 2+}~','3'),
        ('"\144"','"d"'),
        ('[1 2 3]~','1 2 3'),
        ('1`','"1"'),
        ('[1 [2] "asdf"]`','"[1 [2] \\"asdf\\"]"'),
        (' "1"`','"\\"1\\""'),
        ('{1}`','"{1}"'),
        ('1 2 3 4 @','1 3 4 2'),
        ('1 2 3 4 5  1$','1 2 3 4 5 4'),
        ('"asdf"$','"adfs"'),
        ('[5 4 3 1 2]{-1*}$','[5 4 3 2 1]'),
        ('5 7+','12'),
        ('"asdf"{1234}+','{asdf 1234}'),
        ('[1 2 3][4 5]+','[1 2 3 4 5]'),
        ('1 2-3+','1 -1'),
        ('1 2 -3+','1 -1'),
        ('1 2- 3+','2'),
        ('[5 2 5 4 1 1][1 2]-','[5 5 4]'),
        ('2 4*','8'),
        ('2 {2*} 5*','64'),
        ('[1 2 3]2*','[1 2 3 1 2 3]'),
        ('3"asdf"*','"asdfasdfasdf"'),
        ('[1 2 3]","*','"1,2,3"'),
        ('[1 2 3][4]*','[1 4 2 4 3]'),
        ('"asdf"" "*','"a s d f"'),
        ('[1 [2] [3 [4 [5]]]]"-"*',' "1-\\002-\\003\\004\\005" '),
        ('[1 [2] [3 [4 [5]]]][6 7]*','[1 6 7 2 6 7 3 [4 [5]]]'),
        ('[1 2 3 4]{+}*','10'),
        #('"asdf'{+}*",'414'),
        ('7 3 /','2'),
        ('[1 2 3 4 2 3 5][2 3]/','[[1] [4] [5]]'),
        ('"a s d f"" "/','["a" "s" "d" "f"]'),
        ('[1 2 3 4 5] 2/','[[1 2] [3 4] [5]]'),
        ('0 1 {100<} { .@+ } /','89 [1 1 2 3 5 8 13 21 34 55 89]'),
        ('[1 2 3]{1+}/','2 3 4'),
        ('7 3 %','1'),
        #(''assdfs' 's'%','["a" "df"]'),
        #(''assdfs' 's'/','["a" "" "df" ""]'),
        ('[1 2 3 4 5] 2%','[1 3 5]'),
        ('[1 2 3 4 5] -1%','[5 4 3 2 1]'),
        ('[1 2 3]{.}%','[1 1 2 2 3 3]'),
        
        # TODO: Use set() for |&^ aa types
        
        #('5 3 |','7'),
        #('[1 1 2 2][1 3]&','[1]'),
        #('[1 1 2 2][1 3]^','[2 3]'),
        
        ("'\\n'",'"\\n"'),
        ("' \\' "," ' "),
        #(' "\n" ',' "\n" '),
        ('1 2 [\]','[2 1]'),
        ('1 2 3\\','1 3 2'),
        ('1:a a','1 1'),
        ('1:O;O','1'),
        ('1 2 3;','1 2'),
        ('3 4 <','1'),
        #(' "asdf" "asdg" <','1'),
        ('[1 2 3] 2 <','[1 2]'),
        #('{asdf} -1 <','{asd}'),
        ('3 4 >','0'),
        #(' "asdf" "asdg" >','0'),
        ('[1 2 3] 2 >','[3]'),
        #('{asdf} -1 >','{f}'),
        ('3 4 =','0'),
        (' "asdf" "asdg" =','0'),
        ('[1 2 3] 2 =','3'),
        ('{asdf} -1 =','102'),
        ('10,','[0 1 2 3 4 5 6 7 8 9]'),
        ('10,,','10'),
        ('10,{3%},','[1 2 4 5 7 8]'),
        ('1 2 3.','1 2 3 3'),
        ('2 8?','256'),
        ('5 [4 3 5 1] ?','2'),
        ('[1 2 3 4 5 6] {.* 20>} ?','5'),
        ('5(','4'),
        ('[1 2 3](','[2 3] 1'),
        ('5)','6'),
        ('[1 2 3])','[1 2] 3'),
        ('1 2 3 if','2'),
        ('0 2 {1.} if','1 1'),
        ('-2 abs','2'),
        ('5{1-..}do','4 3 2 1 0 0'),
        #('5{.}{1-.}while','4 3 2 1 0 0'),
        ('[[1 2 3][4 5 6][7 8 9]]zip','[[1 4 7] [2 5 8] [3 6 9]]'),
        ('["asdf""1234"]zip','["a1" "s2" "d3" "f4"]'),
        #('[1 1 0] 2 base','6'),
        #('6 2 base','[1 1 0]')
        ('1 1+','2'),
        
        # original test batch
        ("""3 2.""","3 2 2"),
        ("""[3 2].[5]""","[3 2] [3 2] [5]"),
        ("""1 2 3@""","2 3 1"),
        ("""1 2\\""","2 1"),
        ("""1 1+""","2"),
        ("""2 4*""","8"),
        ("""7 3 /""","2"),
        ("""5 2 ?""","25"),
        ("""5`""","\"5\""),
        ("""[1 2 3]`""","\"[1 2 3]\""),
        (""" 3 4 >""","0"),
        ("""[1 2 3 4]{+}*""","10"),
        ("""{[2 3 4] 5 3 6 {.@\%.}*}`""","\"{[2 3 4] 5 3 6 {.@\%.}*}\""),
        (""" 5,`""","\"[0 1 2 3 4]\""),
        ("""[1 2 3 4 5 6]{.* 20>}?""","5"),
        ("""5 1+,1>{*}*""","120"),
        ("""[1 2 3][4 5]+""","[1 2 3 4 5]"),
        ("""5{1-..}do""","4 3 2 1 0 0"),
        ("""2706 410{.@\%.}do;""","82"),
        ("""5 2,~{.@+.100<}do""","5 89 144"),
        ("""5,{1+}%{*}*""","120"),
        # testing quotes
        ('{}','{}'),
        ('[]','[]'),
        ('""','""'),
        ('5','5'),
        ('{}`','"{}"'),
        ('[]`','"[]"'),
        ('""`','"\\"\\""'),
        ('5`','"5"'),
        ('[1 2 3]`','"[1 2 3]"'),
        ('[1 [2] 3]`','"[1 [2] 3]"'),
        ('[1 [2] 3 {.@+}]`','"[1 [2] 3 {.@+}]"'),
        ('[1 [2 "hei"] 3]`','"[1 [2 \\"hei\\"] 3]"'),
        #('139~:@.{0\\`{15&.*+}/}*1=!"happy sad "6/=@,{@\\)%!},,2=4*"non-prime">','happy prime')
    ]
    
    #program = """~:@.{0\`{15&.*+}/}*1=!"happy sad "6/"""
    #  """=@,{@\)%!},,2=4*"non-prime">"""
    #program = """'asdf'{+}*"""
    #program = """99{n+~."+#,#6$DWOXB79Bd")base`1/10/~{~2${~1$+}%(;+~}%""" 
    #  """++=" is "\"."1$4$4-}do;;;"magic." """
    #program = """''6666,-2%{2+.2/@*\/10.3??2*+}*`50<~\;"""
    ntp = Interpreter()
    succ,ran = 0,0
    for it in tests:
        res = ntp._quote(ntp.compile(it[0]))[0][1]
        ran += 1
        if it[1]==res: 
            print "SUCC:",it[0],"=>",res
            succ += 1
        else: 
            print "FAIL:",it[0],"=>",res," | ",it[1]
        ntp.stack = []
    print succ,"/",ran

def run_some_scripts():      
    ntp = Interpreter()
    #"""''66,-2%{2+.2/@*\/10.3??2*+}*`50<~\;"""
    #"""66,-2%{2+.2/@*\/9)499?2*+}*"""
    #""" 7 9000 2?\/ 6+ 7000 2?\/ 6+ 5000 2?\/ 6+ 3000 2? 6+ 1000 2?  """
    program1 = """
    "duplicate n values top of the stack";
    {["{"2$("$}"4$"*"]{+}*\;~}:rg;
    
    "1 2 3 5 8 13 ...";
    ["2rg+..50<E@if~":E; 1 2 E~;];
    """
    
    program2 = '200,{)}%2%700000000+{\\10000*2?100000000*\\/600000000+}*300000000-'
    #2000,{)}%2%B B6++{\A*2?B*\/B6+}*3 B*-
    
    #t1 = time.time()
    #cProfile.compile('ntp.exec_ast(ntp.parser.do(program))')
    #t2 = time.time()
    #print '%0.3f' % (t2-t1)

    ntp.exec_ast(ntp.parser.do(program2))
    print ntp._quote(ntp.stack)[0][1]
    for it in sorted(ntp.profile.items(), key=(lambda x: x[1].time))[::-1]:
        print it[0],"\t",it[1]

logging.basicConfig(level=logging.INFO)

run_tests()
#run_some_scripts()
