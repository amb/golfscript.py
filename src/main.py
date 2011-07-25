import re, logging
from time import sleep

logging.basicConfig(level=logging.INFO)

class Word(object):
    def __init__(self, function, name, types, inputs):
        if name == '': 
            raise ValueError("Invalid name.")
        if len(types) > 0 and len(types) != inputs: 
            raise ValueError("Type definitino does not match input.")
        
        self.name = name
        self.function = function
        self.types = types  
        self.inputs = inputs
        
class Parser(object):
    def __init__(self):
        self.lex = re.compile("""([a-zA-Z_][a-zA-Z0-9_]*)|"""
                              """('(?:\\.|[^'])*'?)|"""
                              """("(?:\\.|[^"])*"?)|"""
                              """(-?[0-9]+)|"""
                              """(#[^\n\r]*)|(.)""", re.M)
        self.noop   = lambda x: x
        self.lexems = ["w",      "s", "s", "i","comment","w"]
        self.conv   = [self.noop,eval,eval,int,self.noop,self.noop]      

    def do(self, prg):
        c=[[(self.lexems[i],self.conv[i](j)) 
            for i,j in enumerate(x) if j != ''][0] 
            for x in self.lex.findall(prg)][::-1]
        logging.debug(c)
        def recurse_blocks(inp):
            s = []
            while True:
                i = c.pop()
                if i[1] == '}': 
                    return ("b",s)
                elif i[1] == '{': 
                    s.append(recurse_blocks(inp))
                else:              
                    s.append(i)
            raise ValueError("Blocks don't match.")
        code = []
        while c:
            i = c.pop()
            if i[1] == '{': 
                code.append(recurse_blocks(c))
            elif i[1] == '}': 
                raise ValueError("Blocks don't match.")
            else:             
                code.append(i)
        return code

class Interpreter(object):
    def __init__(self):
        self.parser = Parser()
        self.words = {}
        self.construct_language()
        
    def exec_ast(self, c, st):
        def try_run(tm,ks):
            logging.debug("try_run: %s %s %s" % (tm,ks,st[-2:]))
            for k in ks:
                # go through possible type set and try to match
                if len(k) <= len(st):
                    t = get_types(len(k))
                    if t == k:     
                        ex_func(tm,t)
                        return True
                else:
                    raise ValueError("Stack underflow. ",st)
    
        def ex_func(tm,t):
            logging.debug("exec: %s %s %s" % (tm,t,st))   
            sp = []
            for _ in range(self.words[tm][t].inputs): sp.append(st.pop())
            r = self.words[tm][t].function(*sp)
            if r: 
                st.extend(r)
            
        def get_types(i):
            return ''.join([x[0] for x in st[-i:]])
        
        def do_op(op):
            if op in self.words:
                # found token in wordlist
                ks = self.words[op].keys()
                if ks[0]: # word has typed parameters
                    if not try_run(op,ks): 
                        # no match found, try and coerce the types to fit
                        if op not in "+-|&^*": # only for these ops
                            raise ValueError("False coerce: %s %s" % (op,ks)) 
                        st[-1],st[-2] = self._coerce(st[-1],st[-2])
                        ex_func(op,get_types(2))
                else: # words with no types
                    ex_func(op,'')
                    
            elif st[-1][1] == ':':
                # variable definition
                st.pop()
                x = st[-1]
                f = (lambda: [x])
                self.words[op] = {'':Word(f,op,'',0)}
                logging.debug("set: %s %s" % (op,st[-1]))
            else:
                raise ValueError("Function not found: %s" % (i[1]))            
        
        # FIXME: stack management might not work properly because
        # if we return from lexical scope, self.stack is still
        # the previous values
        self.stack = st # determine currently active stack
        logging.debug("exec_ast(): %s %s" % (self._quote(c)[0][1], st))
        
        for i in c:
            if i[0] == "w":
                do_op(i[1])
            else:
                st.append(i)
        return st
    
    def run(self, p):
        return self.exec_ast(self.parser.do(p), [])
    
    def add_word(self, n, t, inp):
        def wrap(f):
            if n in self.words:
                self.words[n][t] = Word(f,n,t,inp)
            else:
                self.words[n] = {t:Word(f,n,t,inp)}
            return f
        return wrap
    
    def construct_language(self):
        self.add_word('+', 'ii', 2)(lambda a,b: [('i', a[1]+b[1])])
        self.add_word('+', 'aa', 2)(lambda a,b: [('a', b[1]+a[1])])
        self.add_word('+', 'bb', 2)(lambda a,b: [('b', b[1]+a[1])])
        
        self.add_word('-', 'ii', 2)(lambda a,b: [('i', b[1]-a[1])])
        self.add_word('-', 'aa', 2)(lambda a,b: [('a', [x for x in b[1] if x not in a[1]])])
        
        self.add_word('*', 'ii', 2)(lambda a,b: [('i', a[1]*b[1])])
        self.add_word('*', 'bi', 2)(lambda a,b: [('i', b[1])])
        self.add_word('*', 'ai', 2)(lambda a,b: [('a', b[1]*a[1])])
        self.add_word('*', 'aa', 2)(lambda a,b: [('a', a[1])])
        self.add_word('*', 'ss', 2)(lambda a,b: [('s', a[1])])
        self.add_word('*', 'is', 2)(lambda a,b: [('s', b[1]*a[1])])
        
        @self.add_word('*', 'ab', 2)
        def a_b_mul(a,b):
            while len(b[1])>1:
                i,j = b[1].pop(),b[1].pop()
                b[1].append(self.exec_ast([j]+[i]+a[1], [])[0])
            return b[1]
    
        @self.add_word('/', 'ii', 2)
        def i_i_each(a,b): return [('i', b[1]/a[1])]
        
        @self.add_word('/', 'aa', 2)
        def a_a_each(a,b): return [('a', b[1])]
        
        @self.add_word('/', 'ai', 2)
        def a_i_each(a,b): return [('i', b[1])]
        
        @self.add_word('/', 'bb', 2)
        def b_b_each(a,b): return [('b', b[1])]
        
        @self.add_word('/', 'ab', 2)
        def a_b_each(a,b): return [('b', b[1])]
        
        @self.add_word('/', 'ss', 2)
        def s_s_each(a,b): return [('s', b[1])]
    
    
        @self.add_word('%', 'ii', 2)
        def i_i_mod(a,b): return [('i', b[1]%a[1])]
        
        @self.add_word('%', 'aa', 2)
        def a_a_mod(a,b): raise ValueError("Unimplemented.")
        
        @self.add_word('%', 'ai', 2)
        def a_i_mod(a,b): return [('a', b[1][::a[1]])]
    
        @self.add_word('%', 'ab', 2)
        def a_b_mod(a,b):
            x = []
            for i in b[1]:
                cm = [i]+a[1]
                x.append(self.exec_ast(cm, [])[0])
            return [('a', x)]
    
        self.add_word('?', 'ii', 2)(lambda a,b: [('i', b[1]**a[1])])
        
        @self.add_word('?', 'ia', 2)
        def i_a_poww(a,b):
            for i,j in enumerate(b[1]): 
                if a[1] == j[0]: 
                    return [i]
            return [('i', -1)]
        
        @self.add_word('?', 'ab', 2)
        def a_b_poww(a,b):
            for i in b[1]:
                r = self.exec_ast([i]+a[1], [])
                if r[0] == ('i', 1): 
                    return [i]
                
                
        self.add_word('<', 'ii', 2)(lambda a,b: [('i', 0 if a[1]<b[1] else 1)])
        self.add_word('<', 'ai', 2)(lambda a,b: [('a', [i for i in b[1] if i[1]<a[1]])])
        self.add_word('>', 'ii', 2)(lambda a,b: [('i', 0 if a[1]>b[1] else 1)])
        self.add_word('>', 'ai', 2)(lambda a,b: [('a', [i for i in b[1] if i[1]>=a[1]])])

        self.add_word('=', 'ii', 2)(lambda a,b: [('i', 1 if a[1]==b[1] else 0)])      
        self.add_word('=', 'ss', 2)(lambda a,b: [('i', 1 if a[1]==b[1] else 0)])
        self.add_word('=', 'ai', 2)(lambda a,b: [b[1][a[1]]] if abs(a[1])<len(b[1]) else None)
        self.add_word('=', 'bi', 2)(lambda a,b: [b[1][a[1]]] if abs(a[1])<len(b[1]) else None)
 
        self.add_word('~', 'i', 1)(lambda a: [('i', ~a[1])])
        self.add_word('~', 's', 1)(lambda a: self.exec_ast(self.parser.do(a[1]), []))
        self.add_word('~', 'b', 1)(lambda a: self.exec_ast(a[1], []))
        self.add_word('~', 'a', 1)(lambda a: a[1])
        
        self.add_word(',', 'i', 1)(lambda a: [('a', [('i', x) for x in range(a[1])])])
        self.add_word(',', 'a', 1)(lambda a: [('i', len(a[1]))])
        
        self.add_word(')', 'i', 1)(lambda a: [('i', a[1]+1)])
        self.add_word('(', 'i', 1)(lambda a: [('i', a[1]-1)])
        self.add_word('!', 'i', 1)(lambda a: [('i',1-a[1])])
        self.add_word('\\', '', 2)(lambda a,b: [a,b])
        self.add_word('.', '', 1)(lambda a: [a,a])
        self.add_word(';', '', 1)(lambda a: None)
        self.add_word('@', '', 3)(lambda a,b,c: [b,a,c])
        self.add_word('`', '', 1)(lambda a: self._quote(a))
        self.add_word('[', '', 0)(lambda: [('w','[')])

        @self.add_word(']', '', 0)
        def bracke():        
            l = []
            while self.stack and self.stack[-1][1] != '[': 
                l.append(self.stack.pop())
            if self.stack and self.stack[-1][1] == '[': 
                self.stack.pop()
            self.stack.append(('a', l[::-1]))  
        
        @self.add_word('p', '', 1)
        def pputs(a): print self._quote(a[1])[0][1]
        
        self.add_word(' ', '', 0)(lambda: None)
        self.add_word(':', '', 0)(lambda: [('w',':')])
    
        @self.add_word('do', 'b', 1)
        def b_doo(a): 
            while True:
                self.exec_ast(a[1], self.stack)
                if not self._true(self.stack.pop()): 
                    break

        self.add_word('$', 'i', 1)(lambda a: [self.stack[-(a[1]+1)]])
        self.add_word('$', 'a', 1)(lambda a: ('a', a[1].sort()))
        self.add_word('$', 's', 1)(lambda a: [('s', a[1])])
        self.add_word('$', 'b', 1)(lambda a: [('b', [])])

    # 0 [] "" {} = false, everything else = true
    
    def _false(self, a):
        return a == ('i', 0) or a == ('a', []) or a == ('s', '') or a == ('b', [])
    
    def _true(self, a):
        return not self._false(a)
    
    def _quote(self, a):
        logging.debug("quote:"+repr(a))
        
        def ww(i):
            if i[0] == 'i': return repr(i[1])
            if i[0] == 's': return '"' + i[1] + '"'
            if i[0] == 'w': return i[1]
            if i[0] == 'a': return "[" + ' '.join([ww(x) for x in i[1]]) + "]"
            if i[0] == 'b': return '{' + ''.join([ww(x) for x in i[1]]) + '}'
            
        if isinstance(a, list): 
            t = ' '.join([ww(x) for x in a])
        elif isinstance(a, tuple): 
            t = ww(a)
            
        return [('s', t)]

    def _coerce(self,a,b):
        def _raise(a):
            if a[0] == 'i': return ('a', [a])
            if a[0] == 'a': return ('s', ' '.join([repr(x[1]) for x in a[1]]))
            if a[0] == 's': return ('b', [a])
        
        order = {'i':0,'a':1,'s':2,'b':3}
        logging.debug("coerce: %s %s" % (a,b))
    
        while a[0] != b[0]:
            if order[a[0]] > order[b[0]]: 
                b = _raise(b)
            elif order[b[0]] > order[a[0]]: 
                a = _raise(a)
        
        return a,b
 
def run_tests():
    gs_com = [("""5~""","""-6"""),
              (""""1 2+"~""","""3"""),
              ("""{1 2+}~""","""3"""),
              ("""[1 2 3]~""","""1 2 3"""),
              ("""1`""",'"1"'),
              ("""[1 [2] 'asdf']`""",' \"[1 [2] \\\"asdf\\\"]\"'),
              (""" "1"`""",'""1""'),
              ("""{1}""",""" "{1}" """),
              ("""1 2 3 4 @""","""1 3 4 2"""),
              ("""1 2 3 4 5  1$""","""1 2 3 4 5 4"""),
              ("""'asdf'$""",""" "adfs" """),
              ("""[5 4 3 1 2]{-1*}$""","""[5 4 3 2 1]"""),
              ("""5 7+""","""12"""),
              ("""'asdf'{1234}+""","""{asdf 1234}"""),
              ("""[1 2 3][4 5]+""","""[1 2 3 4 5]"""),
              ("""1 2-3+""","""1 -1"""),
              ("""1 2 -3+""","""1 -1"""),
              ("""1 2- 3+""","""2"""),
              ("""[5 2 5 4 1 1][1 2]-""","""[5 5 4]"""),
              ("""2 4*""","""8"""),
              ("""2 {2*} 5*""","""64"""),
              ("""[1 2 3]2*""","""[1 2 3 1 2 3]"""),
              ("""3'asdf'*""",'"asdfasdfasdf"'),
              ("""[1 2 3]','*""",""" "1,2,3" """),
              ("""[1 2 3][4]*""","""[1 4 2 4 3]"""),
              ("""'asdf'' '*""",""" "a s d f" """),
              ("""[1 [2] [3 [4 [5]]]]'-'*""",""" "1-\002-\003\004\005" """),
              ("""[1 [2] [3 [4 [5]]]][6 7]*""","""[1 6 7 2 6 7 3 [4 [5]]]"""),
              ("""[1 2 3 4]{+}*""","""10"""),
              #("""'asdf'{+}*""","""414"""),
              ("""7 3 /""","""2"""),
              ("""[1 2 3 4 2 3 5][2 3]/""","""[[1] [4] [5]]"""),
              ("""'a s d f'' '/""","""["a" "s" "d" "f"]"""),
              ("""[1 2 3 4 5] 2/""","""[[1 2] [3 4] [5]]"""),
              ("""0 1 {100<} { .@+ } /""","""89 [1 1 2 3 5 8 13 21 34 55 89]"""),
              ("""[1 2 3]{1+}/""","""2 3 4"""),
              ("""7 3 %""","""1"""),
              #("""'assdfs' 's'%""","""["a" "df"]"""),
              #("""'assdfs' 's'/""","""["a" "" "df" ""]"""),
              ("""[1 2 3 4 5] 2%""","""[1 3 5]"""),
              ("""[1 2 3 4 5] -1%""","""[5 4 3 2 1]"""),
              ("""[1 2 3]{.}%""","""[1 1 2 2 3 3]"""),
              #("""5 3 |""","""7"""),
              #("""[1 1 2 2][1 3]&""","""[1]"""),
              #("""[1 1 2 2][1 3]^""","""[2 3]"""),
              #("""'\n'""",""" "\\n" """),
              #("""' \' '""",""" " ' " """),
              #(""" "\n" """,""" "\n" """),
              #(""" "\144" """,""" "d" """),
              ("""1 2 [\]""","""[2 1]"""),
              ('1 2 3',"""1 3 2"""),
              ("""1:a a""","""1 1"""),
              ("""1:O;O""","""1"""),
              ("""1 2 3;""","""1 2"""),
              ("""3 4 <""","""1"""),
              #(""" "asdf" "asdg" <""","""1"""),
              ("""[1 2 3] 2 <""","""[1 2]"""),
              #("""{asdf} -1 <""","""{asd}"""),
              ("""3 4 >""","""0"""),
              #(""" "asdf" "asdg" >""","""0"""),
              ("""[1 2 3] 2 >""","""[3]"""),
              #("""{asdf} -1 >""","""{f}"""),
              ("""3 4 =""","""0"""),
              (""" "asdf" "asdg" =""","""0"""),
              ("""[1 2 3] 2 =""","""3"""),
              ("""{asdf} -1 =""","""102"""),
              ("""10,""","""[0 1 2 3 4 5 6 7 8 9]"""),
              ("""10,,""","""10"""),
              ("""10,{3%},""","""[1 2 4 5 7 8]"""),
              ("""1 2 3.""","""1 2 3 3"""),
              ("""2 8?""","""256"""),
              ("""5 [4 3 5 1] ?""","""2"""),
              ("""[1 2 3 4 5 6] {.* 20>} ?""","""5"""),
              ("""5(""","""4"""),
              ("""[1 2 3](""","""[2 3] 1"""),
              ("""5)""","""6"""),
              ("""[1 2 3])""","""[1 2] 3"""),
              ("""1 2 3 if""","""2"""),
              ("""0 2 {1.} if""","""1 1""")
              ]
    tests = [("""3 2.""","3 2 2"),
             ("""[3 2].[5]""","[3 2] [3 2] [5]"),
             ("""1 2 3@""","2 3 1"),
             ("""1 2\\""","2 1"),
             ("""1 1+""","2"),
             ("""2 4*""","8"),
             ("""7 3 /""","2"),
             ("""5 2 ?""","25"),
             ("""5`""","5"),
             ("""[1 2 3]`""","[1 2 3]"),
             (""" 3 4 >""","0"),
             ("""[1 2 3 4]{+}*""","10"),
             ("""{[2 3 4] 5 3 6 {.@\%.}*}`""","{[2 3 4] 5 3 6 {.@\%.}*}"),
             (""" 5,`""","[0 1 2 3 4]"),
             ("""[1 2 3 4 5 6]{.* 20>}?""","5"),
             ("""5 1+,1>{*}*""","120"),
             ("""[1 2 3][4 5]+""","[1 2 3 4 5]"),
             ("""5{1-..}do""","4 3 2 1 0 0"),
             ("""2706 410{.@\%.}do;""","82"),
             ("""5 2,~{.@+.100<}do""","5 89 144"),
             ("""5,{1+}%{*}*""","120")]
    
    #program = """~:@.{0\`{15&.*+}/}*1=!"happy sad "6/=@,{@\)%!},,2=4*"non-prime">"""
    #program = """'asdf'{+}*"""
    #program = """99{n+~."+#,#6$DWOXB79Bd")base`1/10/~{~2${~1$+}%(;+~}%++=" is "\"."1$4$4-}do;;;"magic." """
    #program = """''6666,-2%{2+.2/@*\/10.3??2*+}*`50<~\;"""
    ntp = Interpreter()
    for it in gs_com:
        #print it
        #try:
        res = ntp._quote(ntp.run(it[0]))[0][1]
        if it[1]==res: 
            print "SUCC:",it[0],"=>",res
        else: 
            print "FAIL:",it[0],"=>",res," | ",it[1]
        ntp.stack = []

run_tests()           
#print exec_ast(interpret("""5:B;B"""), [])
