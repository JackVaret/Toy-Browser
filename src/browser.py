
import tkinter
from url import http
server_socket_dict = dict()
redirect_count = 0
WIDTH,HEIGHT = 800,600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
cursor_x, cursor_y = HSTEP, VSTEP

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            scrollregion=(0,0,2000,2000)
        )
        self.scroll = 0
        self.scrollbar = tkinter.Scrollbar(self.window, orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.place(relx=1,rely=0,relheight=1,anchor='ne')
        self.scrollbar.bind("<ButtonRelease-1>",self.manage_scrollbar)
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<Configure>", self.configure)
    def configure(self,e):
        global WIDTH
        global HEIGHT
        WIDTH = e.width
        HEIGHT = e.height
        self.canvas.pack(fill='both',expand=1)
        self.display_list, self.endypos = layout(self.text)
    def manage_scrollbar(self,e):
        relative_top_scrollbar_position = self.scrollbar.get()[0]
        relative_bottom_scrollbar_position = self.scrollbar.get()[1]
        if relative_top_scrollbar_position ==0.0:
            self.scroll = 0
        elif relative_bottom_scrollbar_position == 1:
            self.scroll = self.endypos
        else:
            self.scroll = self.endypos * (relative_bottom_scrollbar_position + relative_top_scrollbar_position)/2
        self.draw()
    def scrolldown(self, e):
        if self.scroll + SCROLL_STEP > self.display_list[-1][1]:
            self.scroll = self.display_list[-1][1]
        else:
            self.scroll += SCROLL_STEP
        self.scrollbar.set(1*(self.scroll/self.endypos)-.3,1*self.scroll/self.endypos)
        self.draw()
    def scrollup(self,e):
        self.scroll -= SCROLL_STEP
        if self.scroll < 0:
            self.scroll = 0
        self.scrollbar.set(1*(self.scroll/self.endypos)-.3,1*self.scroll/self.endypos)
        self.draw()
    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y> self.scroll + HEIGHT:
                continue
            if y + VSTEP<self.scroll:
                continue
            self.canvas.create_text(x,y - self.scroll, text =c)
    def load(self,url):
        global HSTEP, VSTEP, cursor_x, cursor_y
        self.canvas.create_rectangle(10,20,400,300)
        self.canvas.create_oval(100, 100, 150, 150)
        self.canvas.create_text(200, 150, text="Hi!")
        self.text = lex(url.request())
        self.display_list, self.endypos = layout(self.text)
        self.draw()
def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        # Creates new lines when x is past the page
        if cursor_x >= WIDTH - HSTEP or c == '\n':
            cursor_y += VSTEP + 10
            cursor_x = HSTEP
    # Represents the lowest y value of any displayed content
    end_ypos = display_list[-1][1]
    return display_list, end_ypos

def lex(body, mode='r'):
    entity = ''
    text = ""
    creating_entity = False
    if mode =="r":
        in_tag = False
        for c in body:
            if c =='&':
                creating_entity = True
                entity+=c
            if c== "<":
                in_tag = True
            elif c == ">":
                in_tag = False
            elif not in_tag:
                    if creating_entity:
                        if c != 'l' and c != 'g':
                            creating_entity = False
                            text+= (entity + c)
                            entity = ''
                        else:
                            entity+=c
                            if len(entity) ==4:
                                if entity == '&lt;':
                                    text+= "<"
                                    creating_entity = False
                                    entity = ''
                                elif entity == '&gt;':
                                    text += ">"
                                    creating_entity = False
                                    entity = ''
                    else:
                        text += c
        return text
    elif mode =='s':
        text = body
        return text



def load(url):
    global redirect_count
    body = url.request()
    if url.scheme == 'view-source':
        lex(body,'s')
        redirect_count = 0
    else:
        lex(body)
        redirect_count = 0

if __name__ == "__main__":
    import sys
    Browser().load(http.URL(sys.argv[1]))
    tkinter.mainloop()
