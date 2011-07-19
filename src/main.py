import re

input = """2706 410"""; program = """~{.@\%.}do;"""

# input = """5"""; program = """ 1+,1>{*}*"""
# program = """ 3 4 >"""
# program = """[1 2 3][4 5]+"""
# program = """1 1+"""
# program = """,{1+}%{*}*"""
# program = """~:@.{0\`{15&.*+}/}*1=!"happy sad "6/=@,{@\)%!},,2=4*"non-prime">"""
program = input + program

lex=re.compile("""([a-zA-Z_][a-zA-Z0-9_]*)|('(?:\\.|[^'])*'?)|("(?:\\.|[^"])*"?)|(-?[0-9]+)|(#[^\n\r]*)|(.)""")
noop = lambda x: x
lexems=["w","s","s","i","comment","w"]
conv  =[noop,eval,eval,int,noop,noop ]
cmds=[[(lexems[i],conv[i](j)) for i,j in enumerate(x) if j != ''][0] for x in lex.findall(program)]

toks="""~ ` ! @ $ + - * / % | & ^ \ ; < > = , . ? ( ) 
        and or xor print rand do while until if abs zip base"""
        
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
          ")":"inc",
          "(":"dec",
          " ":"none",
          "[":"bracko",
          "]":"bracke",
          ";":"drop",
          "<":"lessert",
          ">":"greatert",
          
          "do":"doo"
          }
        
# int array string block (word) (any)
types=["i","a","s","b"] # + - ^ & | 

# -- start of parsing
cmds = cmds[::-1]
def interpret(c):
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
        if   i[1] == '{': code.append(recurse_blocks(cmds))
        elif i[1] == '}': raise ValueError("Blocks don't match.")
        else:             code.append(i)
    return code[::-1]

ast = interpret(cmds)

stack = []

def _int(a): return ("i", a)  
def _arr(a): return ("a", a)

def funcs():
    # ~
    def i_bitwise(a): return _int(~a[0][1])
    def s_bitwise(a): pass
    def b_bitwise(a): pass
    def a_bitwise(a): pass # map int_bitwise
    
    # `
    def quote(a): pass
    
    # !
    def exlamation(a): return _int(1-a[1])
    
    # @
    def rot3(a,b,c): return b,c,a
    
    # $
    def i_dollar(a,b): pass
    def a_dollar(a): pass
    def b_dollar(a,b): pass
    
    # +
    def i_i_plus(a): return _int(a[0][1]+a[1][1])
    def a_a_plus(a): return _arr(a[0][1]+a[1][1])
    def b_b_plus(a): return ('b', a[0][1]+a[1][1])
    
    # -
    def i_i_sub(a,b): return _int(a[1]-b[1])
    
    # *
    def i_i_mul(a): return _int(a[0][1]*a[1][1])
    def b_i_mul(a): pass
    def a_i_mul(a): pass
    def a_a_mul(a): pass
    def a_b_mul(a):
        x = a[1][1]
        while len(x)>1:
            b,c = x.pop(),x.pop()
            cm = a[0][1]+[b]+[c]
            print cm
            x.append(exec_ast(cm)[0])
        return x[0]
    
    # /
    def i_i_each(a): pass
    def a_a_each(a): pass
    def a_i_each(a): pass
    def b_b_each(a): pass
    def a_b_each(a): pass
    
    # %
    def i_i_mod(a): pass
    def a_a_mod(a): pass
    def a_i_mod(a): pass

    def a_b_mod(a):
        x = []
        for i in a[1][1]:
            cm = [i]+a[0][1]
            x.append(exec_ast(cm[::-1])[0])
        return _arr(x)
    
    # \
    def swap(a): 
        print "swap"
        return a[1],a[0]
    
    # ;
    def drop(): return None
    
    # ,
    def i_comma(a): return ("a", [_int(x) for x in range(a[0][1])])
    
    # .
    def dup(a): pass
    
    # )
    def i_inc(a): return _int(a[1]+1)
    
    # (
    def i_dec(a): return _int(a[1]-1)
    
    # " "
    def none(): return None
    
    # [
    def bracko(): return ('w','[')
    
    # ]
    def bracke(): return ('w', ']')
       
    # <
    def i_i_lessert(a): return _int(0 if a[0][1]<a[1][1] else 1)
    def a_i_lessert(a): return _arr([i for i in a[1][1] if i[1]<a[0][1]])
        
    # >
    def i_i_greatert(a): return _int(0 if a[0][1]>a[1][1] else 1)
    def a_i_greatert(a): return _arr([i for i in a[1][1] if i[1]>=a[0][1]])
        
    # do
    def b_doo(a): 
        x = exec_ast(a[0][1][::-1])
        print x
        return None

    return locals()

words = {}
for k,v in funcs().iteritems():
    a = k.split('_')
    t,n = ''.join(a[:-1]), a[-1]
    if n in words: 
        words[n][t] = v
    else:
        words[n] = {t:v}

def exec_ast(c):
    global stack
    print "XX execute:",c
    while c:
        i = c.pop()
        print stack
        if i[0] == "w":
            # operator
            tm = tokmap[i[1]]
            ks = words[tm].keys()
            
            if ks != ['']: # skip printing no-argument words
                print ">> stack:", stack[-3:]
                print ">> word:",i[1],"=",tm,ks

            mm = False
            if ks[0] != '':
                for k in ks:
                    # go through possible type set and try to match
                    if len(k) <= len(stack):
                        t = ''.join( [x[0] for x in stack[-len(k):]] )
                        if t == k:     
                            # match found
                            mm = True
                            print "match:",tm,"| type:",t
                            sp = []
                            for _ in range(len(t)):
                                sp.append(stack.pop())
                            r = words[tm][t](sp)
                            if r: 
                                stack.append(r)
                                print "append:",r
                                break
                    else:
                        print "EE Stack underflow. ",stack
            else:
                if i[1] == '[': stack.append(('w','['))
                if i[1] == ']': 
                    l = []
                    while stack and stack[-1][1] != '[':
                        l.append(stack.pop())
                    stack.pop()
                    print "append:",_arr(l)
                    stack.append(_arr(l))
                if i[1] == ';':
                    stack.pop()
                if i[1] == '.':
                    a = stack.pop()
                    stack.append(a); stack.append(a)
        else:
            # not a word, just add to stack
            stack.append(i)
    print "exit:",stack
    return stack
            
exec_ast(ast)
