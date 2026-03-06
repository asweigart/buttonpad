import buttonpad

layout = """
A,B,C,D,E,F
G,H,I,J,K,L
M,N,O,P,Q,R
S,T,U,V,W,X
Y,Z,0,1,2,3
4,5,6,7,8,9"""

bp = buttonpad.ButtonPad(
    layout,
    cell_width=60,
    cell_height=60,
    title="Pretty Buttons That Don't Do Anything"
)

for y in range(6):
    for x in range(6):
        bp[x, y].bg_color = ['red', 'orange', 'yellow', 'green', 'blue', 'purple'][y]

bp.run()
