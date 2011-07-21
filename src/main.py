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

stack = []
# 0 [] "" {} = false, everything else = true
def _false(a):
    return a == ('i', 0) or a == ('a', []) or a == ('s', '') or a == ('b', [])
def _true(a):
    return not _false(a)

def _push(a): stack.append(a)
def _pop():   return stack.pop()

def funcs():
    global stack

    def i_bitwise(a): return ('i', ~a[0][1])
    def s_bitwise(a): raise ValueError("Unimplemented.")
    def b_bitwise(a): raise ValueError("Unimplemented.")
    def a_bitwise(a):  
        for x in a[0][1]: _push(x)

    def i_dollar(a,b): raise ValueError("Unimplemented.")
    def a_dollar(a): raise ValueError("Unimplemented.")
    def b_dollar(a,b): raise ValueError("Unimplemented.")

    def i_i_plus(a): return ('i', a[0][1]+a[1][1])
    def a_a_plus(a): return ('a', a[1][1]+a[0][1])
    def b_b_plus(a): return ('b', a[1][1]+a[0][1])

    def i_i_sub(a): return ('i', a[1][1]-a[0][1])

    def i_i_mul(a): return ('i', a[0][1]*a[1][1])
    def b_i_mul(a): raise ValueError("Unimplemented.")
    def a_i_mul(a): raise ValueError("Unimplemented.")
    def a_a_mul(a): raise ValueError("Unimplemented.")
    def a_b_mul(a):
        x = a[1][1]
        while len(x)>1:
            b,c = x.pop(),x.pop()
            logging.debug(repr(b)+repr(c))
            cm = a[0][1][::-1]+[b]+[c]
            logging.debug(""+repr(cm))
            x.append(exec_ast(cm, [])[0])
        return x[0]

    def i_i_each(a): return ('i', a[1][1]/a[0][1])
    def a_a_each(a): raise ValueError("Unimplemented.")
    def a_i_each(a): raise ValueError("Unimplemented.")
    def b_b_each(a): raise ValueError("Unimplemented.")
    def a_b_each(a): raise ValueError("Unimplemented.")

    def i_i_mod(a): return ('i', a[0][1]%a[1][1])
    def a_a_mod(a): raise ValueError("Unimplemented.")
    def a_i_mod(a): return ('a', a[1][1][::a[0][1]])

    def a_b_mod(a):
        x = []
        for i in a[1][1]:
            cm = [i]+a[0][1]
            x.append(exec_ast(cm[::-1], [])[0])
        return ('a', x)

    def i_comma(a): return ("a", [('i', x) for x in range(a[0][1])])

    def i_i_poww(a): return ('i', a[1][1]**a[0][1])
    def i_a_poww(a):
        for i,j in enumerate(a[0][1]): 
            logging.debug("i_a_poww(): "+repr(i)+repr(j)+repr(a[1]))
            if a[1][0] == j[0] and a[1][1] == j[1]: return i
        return('i', -1)
    def a_b_poww(a):
        for i in a[1][1]:
            r = exec_ast(a[0][1][::-1]+[i], stack)
            _pop()
            if r[0] == ('i', 1): return i

    def i_inc(a): return ('i', a[0][1]+1)
    def i_dec(a): return ('i', a[0][1]-1)

    def i_i_lessert(a): return ('i', 0 if a[0][1]<a[1][1] else 1)
    def a_i_lessert(a): return ('a', [i for i in a[1][1] if i[1]<a[0][1]])

    def i_i_greatert(a): return ('i', 0 if a[0][1]>a[1][1] else 1)
    def a_i_greatert(a): return ('a', [i for i in a[1][1] if i[1]>=a[0][1]])
 
    def b_doo(a): 
        while True:
            exec_ast(a[0][1][::-1], stack)
            if not _true(_pop()): break
    
    def swap(): a=_pop(); b=_pop(); _push(a); _push(b);
    def drop(): 
        if stack: stack.pop()
    def dup(): a = stack.pop(); stack.append(a); stack.append(a)
    def exlamation(a): return ('i',1-a[1])
    def rot3(): a=_pop(); b=_pop(); c=_pop(); _push(a); _push(c); _push(b);  
    def quote(): 
        a = _pop()
        logging.debug("quote():"+repr(a))
        def ww(i):
            if i[0] == 'i': return repr(i[1])
            if i[0] == 's': return i[1] #'\"' + i[1] + '\"'
            if i[0] == 'w': return i[1]
            if i[0] == 'a': return "[" + ' '.join([ww(x) for x in i[1]]) + "]"
            if i[0] == 'b': return '{' + ''.join([ww(x) for x in i[1]]) + '}'
            
        if type(a) == type([]): t = ' '.join([ww(x) for x in a])
        else: t = ww(a)
        logging.debug("quote():"+repr(t))
        return t
    
    def none(): return None

    def bracko(): return ('w','[')
    def bracke():
        l = []
        while stack and stack[-1][1] != '[':
            l.append(stack.pop())
        stack.pop()
        stack.append(('a', l[::-1]))
        
    def pputs(): 
        print quote()
        
    return locals()

words = {}
for k,v in funcs().iteritems():
    a = k.split('_')
    t,n = ''.join(a[:-1]), a[-1]
    if n in words: 
        words[n][t] = v
    else:
        words[n] = {t:v}

def exec_ast(c, st):
    logging.debug("exec_ast():"+repr(c))
    while c:
        i = c.pop()
        if i[0] == "w":
            # operator
            tm = tokmap[i[1]]
            ks = words[tm].keys()
            
            if ks != ['']: # skip printing no-argument words
                logging.debug(">> stack:"+repr(st))
                logging.debug(">> word:"+repr(i[1])+"="+repr(tm)+repr(ks))

            mm = False
            if ks[0] != '':
                for k in ks:
                    # go through possible type set and try to match
                    if len(k) <= len(st):
                        t = ''.join([x[0] for x in st[-len(k):]])
                        if t == k:     
                            # match found
                            mm = True
                            logging.debug("match:"+tm+" | type:"+t)
                            sp = []
                            for _ in range(len(t)):
                                sp.append(st.pop())
                            r = words[tm][t](sp)
                            if r: 
                                st.append(r)
                                logging.debug("PUSH:"+repr(r))
                            break
                    else:
                        raise ValueError("Stack underflow.")
                if not mm: raise ValueError("Unable to match instruction:"+
                                            repr(tm)+","+repr(ks)+","+
                                            repr([x[0] for x in st[-3:]]))
            else:
                # words with no defined types
                r = words[tm]['']()
                logging.debug("Executed:"+repr(tm))
                if r: 
                    logging.debug("append:"+repr(r))
                    st.append(r)
        else:
            # not a word, just add to stack
            st.append(i)
    logging.debug("exit:"+repr(stack))
    return st[:]
      
def run_tests():
    global stack
    tests = {
             """5 2,~{..p@+.100<}do""":"",
             """[1 2 3 4]{+}*""":"",
             """2 4*""":"",
             """7 3 /""":"",
             """5 2 ?""":"",
             """[1 2 3 4 5 6]{.* 20>}?""":"",
             """5`""":"",
             """[1 2 3]`""":"",
             """{[2 3 4] 5 3 6 {.@\%.}*}`""":"",
             """ 5,`""":"",
             """2706 410{.@\%.}do;""":"",
             """5{1-..}do""":"",
             """5 1+,1>{*}*""":"",
             """ 3 4 >""":"",
             """[1 2 3][4 5]+""":"",
             """1 1+""":"",
             """5,{1+}%{*}*""":""
             }
    
    for i,j in tests.iteritems():
        try:
            stack = []
            print i,"=>\t\t",exec_ast(interpret(i), stack),j
        except:
            print "FAIL:",i,j

run_tests()           
#print exec_ast(interpret(program), stack)
