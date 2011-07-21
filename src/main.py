import re, logging, inspect
from time import sleep

logging.basicConfig(level=logging.INFO)

#program = """~:@.{0\`{15&.*+}/}*1=!"happy sad "6/=@,{@\)%!},,2=4*"non-prime">"""
#program = """'asdf'{+}*"""
#program = """99{n+~."+#,#6$DWOXB79Bd")base`1/10/~{~2${~1$+}%(;+~}%++=" is "\"."1$4$4-}do;;;"magic." """
#program = """''6666,-2%{2+.2/@*\/10.3??2*+}*`50<~\;"""
#program = """''6666,-2%{2+.2/@*\/10.3??2*+}*"""

lex     = re.compile("""([a-zA-Z_][a-zA-Z0-9_]*)|"""
                     """('(?:\\.|[^'])*'?)|"""
                     """("(?:\\.|[^"])*"?)|"""
                     """(-?[0-9]+)|"""
                     """(#[^\n\r]*)|(.)""", re.M)
noop   = lambda x: x
lexems = ["w","s","s","i","comment","w"]
conv   = [noop,eval,eval,int,noop,noop ]
     
tokmap = {"~":"bitwise",
          "`":"quote",
          "!":"exclamation",
          "@":"rot3",
          "$":"dollar",
          "+":"plus",
          "-":"sub",
          "/":"each",
          "*":"mul",
          "%":"mod",
          "\\":"swap",
          ",":"comma",
          ".":"dup",
          "?":"poww",
          ")":"inc",
          "(":"dec",
          " ":"none",
          "[":"bracko",
          "]":"bracke",
          ";":"drop",
          "<":"lessert",
          ">":"greatert",
          ":":"sett",
          
          "do":"doo",
          "p":"pputs"
          }

def interpret(prg):
    c=[[(lexems[i],conv[i](j)) for i,j in enumerate(x) if j != ''][0] 
      for x in lex.findall(prg)][::-1]
    logging.debug(c)
    def recurse_blocks(inp):
        s = []
        while True:
            i = c.pop()
            if    i[1] == '}': return ("b",s)
            elif  i[1] == '{': s.append(recurse_blocks(inp))
            else:              s.append(i)
        raise ValueError("Blocks don't match.")
    code = []
    while c:
        i = c.pop()
        if   i[1] == '{': code.append(recurse_blocks(c))
        elif i[1] == '}': raise ValueError("Blocks don't match.")
        else:             code.append(i)
    return code[::-1]

# 0 [] "" {} = false, everything else = true

def _false(a):
    return a == ('i', 0) or a == ('a', []) or a == ('s', '') or a == ('b', [])
def _true(a):
    return not _false(a)

def _quote(a):
    logging.debug(a)
    def ww(i):
        if i[0] == 'i': return repr(i[1])
        if i[0] == 's': return i[1] #'\"' + i[1] + '\"'
        if i[0] == 'w': return i[1]
        if i[0] == 'a': return "[" + ' '.join([ww(x) for x in i[1]]) + "]"
        if i[0] == 'b': return '{' + ''.join([ww(x) for x in i[1]]) + '}'
    if   type(a) == type([]): t = ' '.join([ww(x) for x in a])
    elif type(a) == type(()): t = ww(a)
    return ('s', t)

def funcs():
    def i_i_plus(a,b): return ('i', a+b)
    def a_a_plus(a,b): return ('a', b+a)
    def b_b_plus(a,b): return ('b', b+a)

    def i_i_sub(a,b): return ('i', b-a)

    def i_i_mul(a,b): return ('i', a*b)
    def b_i_mul(a,b): raise ValueError("Unimplemented.")
    def a_i_mul(a,b): raise ValueError("Unimplemented.")
    def a_a_mul(a,b): raise ValueError("Unimplemented.")
    def a_b_mul(a,b):
        x = b
        while len(x)>1:
            i,j = x.pop(),x.pop()
            cm = a[::-1]+[i]+[j]
            x.append(exec_ast(cm, [])[0])
        return x[0]

    def i_i_each(a,b): return ('i', b/a)
    def a_a_each(a): raise ValueError("Unimplemented.")
    def a_i_each(a): raise ValueError("Unimplemented.")
    def b_b_each(a): raise ValueError("Unimplemented.")
    def a_b_each(a): raise ValueError("Unimplemented.")

    def i_i_mod(a,b): return ('i', b%a)
    def a_a_mod(a,b): raise ValueError("Unimplemented.")
    def a_i_mod(a,b): return ('a', b[::a])

    def a_b_mod(a,b):
        x = []
        for i in b:
            cm = [i]+a
            x.append(exec_ast(cm[::-1], [])[0])
        return ('a', x)

    def i_i_poww(a,b): return ('i', b**a)
    def i_a_poww(a,b):
        for i,j in enumerate(b): 
            if i == j[0]: return i
        return ('i', -1)
    def a_b_poww(a,b):
        for i in b:
            r = exec_ast(a[::-1]+[i], [])
            if r[0] == ('i', 1): return i

    def i_i_lessert(a,b): return ('i', 0 if a<b else 1)
    def a_i_lessert(a,b): return ('a', [i for i in b if i[1]<a])
    def i_i_greatert(a,b): return ('i', 0 if a>b else 1)
    def a_i_greatert(a,b): return ('a', [i for i in b if i[1]>=a])

    def i_bitwise(a): return ('i', ~a[0][1])
    def s_bitwise(a): raise ValueError("Unimplemented.")
    def b_bitwise(a): raise ValueError("Unimplemented.")
    def a_bitwise(a): return a

    def i_dollar(a): raise ValueError("Unimplemented.")
    def a_dollar(a): raise ValueError("Unimplemented.")
    def b_dollar(a): raise ValueError("Unimplemented.")

    def i_comma(a): return ('a', [('i', x) for x in range(a)])
    def i_inc(a): return ('i', a+1)
    def i_dec(a): return ('i', a-1)
    
    def i_exlamation(a): return ('i',1-a)
    
    def swap(a,b): return [a,b]
    def dup(a): return [a,a]
    def drop(a): return None
    
    def rot3(a,b,c): return [b,a,c] 
    def quote(a): return _quote(a)
    def none(): pass
    def bracko(): return ('w','[')
    def pputs(): print quote()[1]
    
    def sett(): return ('w',':')

    # -- functions that needs full stack
    def b_doo(a,s): 
        while True:
            exec_ast(a[::-1], s)
            if not _true(s.pop()): break
    
    def bracke(s):        
        l = []
        while s and s[-1][1] != '[':
            l.append(s.pop())
        if s and s[-1][1] == '[': s.pop()
        s.append(('a', l[::-1]))            
  
    return locals()

words = {}
for k,v in funcs().iteritems():
    a = k.split('_')
    t,n = ''.join(a[:-1]), a[-1]
    if n in words: 
        words[n][t] = v
    else:
        words[n] = {t:v}
        
# words that need the whole stack
stackwords = set(['bracke', 'doo'])

def exec_ast(c, st):
    logging.debug("exec_ast():"+_quote(c[::-1])[1]+repr(st))
    while c:
        i = c.pop()
        if i[0] == "w":
            # operator
            if i[1] in tokmap:
                # found token in wordlist
                tm = tokmap[i[1]]
                ks = words[tm].keys()
            elif st[-1][1] == ':':
                # variable definition
                words[i[1]]={'':(lambda: st[-2][1])}
            else:
                raise ValueError("Function not found:"+repr(i[1]))
                
            mm = False
            if ks[0] != '':
                for k in ks:
                    # go through possible type set and try to match
                    if len(k) <= len(st):
                        t = ''.join([x[0] for x in st[-len(k):]])
                        if t == k:     
                            # match found
                            mm = True
                            
                            sp = []
                            for _ in range(len(t)): sp.append(st.pop()[1])
                            if tm in stackwords: sp.append(st)

                            logging.debug("exec:"+tm+repr(sp)+repr(st))   
                            r = words[tm][t](*sp)
                            if r: 
                                if type(r)==type([]): st.extend(r)
                                else: st.append(r)
                                logging.debug("PUSH:"+repr(r))
                            break
                    else:
                        raise ValueError("Stack underflow. ",st)
                if not mm: raise ValueError("Unable to match instruction:"+
                                            repr(tm)+","+repr(ks)+","+
                                            repr([x[0] for x in st[-3:]]))
            else:
                # words with no types
                sp = []
                wl = len(inspect.getargspec(words[tm][''])[0])
                if tm in stackwords: sp.append(st)
                else:
                    for _ in range(wl): sp.append(st.pop())

                logging.debug("exec:"+tm+repr(sp)+repr(st))    
                r = words[tm][''](*sp)

                if r: 
                    if type(r)==type([]): st.extend(r)
                    else: st.append(r)
                    logging.debug("a:"+repr(r))
        else:
            # not a word, just add to stack
            st.append(i)
    return st[:]
      
def run_tests():
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
    
    for it in tests:
        try:
            stack = []
            res = _quote(exec_ast(interpret(it[0]), stack))[1]
            if it[1]==res: pass #print "SUCC:",it[0],"=>",res
            else: print "FAIL:",it[0],"=>",res
        except a:
            print "FAIL:",it[0],it[1]

#run_tests()           
print exec_ast(interpret("""5:B;B"""), [])
