import re
import sys
from PIL import Image
from io import BytesIO
import base64

if len(sys.argv) != 2:
    print("Usage: " + sys.argv[0] + " [input file]")
    exit(1)

frameLookup = {}
frameCode = []
frameKey = []
layout = []
unnamed = []
imgs = []
defaults = []

def parse(filename):
    file = open(filename)
    lines = file.readlines()
    if lines[0] != "ETXT0.1\n":
        print("Wrong filetype.")
        exit(1)
    lines
    isImg = False
    curImg = ""
    for line in lines[1:]:
        if isImg:
            if line == "}}\n":
                imgs.append(curImg)
                curImg = ""
                isImg = False
            else:
                curImg += line[:-1]
        elif line == "{{\n":
            isImg = True
        elif line[0:4] == "text":
            text = line[0:-1]
            text = re.split("(?<=[^\x07])_", text)
            text = list(map(lambda s: s.replace("\x07", ""), text))
            unnamed.append(text)
        elif line[0:7] == "default":
            global defaults
            data = line[:-1]
            defaults = data.split(" ")[1:]
        elif line[0:4] == "path":
            coords = line[0:-1]
            coords = coords.split(" ")
            val = []
            inVal = []
            n = 0
            for x in coords[1:]:
                n += 1
                inVal.append(int(x))
                if n % 4 == 0:
                    val.append(inVal)
                    inVal = []
            coords = [coords[0]] + val
            unnamed.append(coords)
        elif line[0:9] == "frameCode":
            global frameCode
            frameCode = line[:-1].split(" ")[1:]
        elif line[0:11] == "frameLookup":
            node = line[:-1].split(" ")
            for x in range(1, len(node) - 1, 2):
                frameLookup[node[x]] = node[x+1]
        elif line[0:5] == "color":
            node = line[:-1]
            node = node.split(" ")
            unnamed.append(node)
        elif line[0:8] == "frameKey":
            global frameKey
            tmp = line[:-1].split(" ")[1:]
            if '-' in line:
                inner = []
                outter = []
                for x in tmp:
                    if x == '-':
                        frameKey.append(inner)
                        inner = []
                    else:
                        inner.append(int(x))
                frameKey.append(inner)
            else:
                frameKey = [list(map(int, tmp))]
        elif len(line) != 1 and line[0] != '#':
            node = line[:-1].strip()
            node = node.split(" ")
            num = list(map(int, node[1:]))
            node = [node[0]] + num
            unnamed.append(node)
    for x in frameCode:
        if x == 'i':
            continue
        target = frameLookup[x]
        frameLookup[x] = list(filter(lambda x: x[0] == target, unnamed))[0][1:]
    frameLookup['i'] = imgs
    global layout
    layout = list(filter(lambda x: x[0] == "layout", unnamed))[0][1:]

def reshape():
    global layout
    frms = []
    for x in range(layout.pop(0)):
        frame = []
        for y in frameKey[x]:
            inner = []
            for z in range(layout.pop(0)):
                inner.append(layout.pop(0))
            frame.append(inner)
        frms.append(frame)
    layout = frms

def imgStr(b64, form, width, height, no):
    return '<image id="Image' + str(no) + '" xlink:href="data:image/' + str.lower(form) + ';base64,' + str(b64) + '" width="' + str(width) + '" height="' + str(height) + '" />'

def pthStr(no, coords):
    vals = []
    # number lookup
    vals.append(frameLookup['x'][coords[0]])
    vals.append(frameLookup['y'][coords[1]])
    vals.append(frameLookup['x'][coords[2]])
    vals.append(frameLookup['y'][coords[3]])
    return '<path id="Path' + str(no) + '" fill="none" stroke="none" d="M' + str(vals[0]) + ',' + str(vals[1]) + ' L' + str(vals[2]) + ',' + str(vals[3]) +'" />'
        
def txtStr(codes, no, frm):
    txt = '<text '
    pth = ""
    for i in range(4, len(codes)):
        c = frameCode[codes[i]]
        if c == 'x':
            val = layout[frm][i][no]
            if val != -1:
                txt += 'x="' + str(frameLookup['x'][val]) + '" '
        elif c == 'y':
            val = layout[frm][i][no]
            if val != -1:
                txt += 'y="' + str(frameLookup['y'][val]) + '" '
        elif c == 'p':
            val = layout[frm][i][no]
            if val != -1:
                pth = '<textPath xlink:href="#Path' + str(val) + '">'
        elif c == 'c':
            val = layout[frm][i][no]
            if val != -1:
                txt += 'fill="' + frameLookup['c'][val] + '" '
        elif c == 'b':
            val = layout[frm][i][no]
            if val != -1:
                txt += 'stroke="' + frameLookup['b'][val] + '" '
        elif c == 's':
            val = layout[frm][i][no]
            if val != -1:
                txt += 'font-size="' + str(frameLookup['s'][val]) + '" '
        elif c == 'w':
            val = layout[frm][i][no]
            if val != -1:
                txt += 'stroke-width="' + str(frameLookup['w'][val]) + '" '
        elif c == 'f':
            val = layout[frm][i][no]
            if val != -1:
                txt += 'font-family="' + frameLookup['f'][val] + '" '
    textNo = layout[frm][3][no]
    if pth != "":
        txt += '>' + pth + frameLookup['t'][textNo] + '</textPath></text>\n'
    else:
        txt += '>' + frameLookup['t'][textNo] + '</text>\n'
    return txt
            



def toSVG(frameNo):
    global layout
    section = layout[frameNo]
    key = frameKey[frameNo]
    svg = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="' + defaults[0] + '" height="' + defaults[1] + '" style="white-space: pre;">\n<defs>\n'

    # image has to be layed out starting with images
    # then followed by x and y coordinates
    # then text followed by x and y coordinates
    # then optional text variables
    # so places 0, 1, 2, 3, 4, 5 in the frameKey are
    # always predetermined

    used = []
    for i in range(len(section[0])):
        #base64 reading of image
        num = section[0][i]
        if num in used:
            continue
        used.append(num)
        data = frameLookup[frameCode[key[0]]][num]
        im = Image.open(BytesIO(base64.b64decode(data)))
        svg += imgStr(data, str.lower(im.format), im.width, im.height, num) + '\n'

    pathIdx = None
    for x in range(len(key)):
        if frameCode[key[x]] == 'p':
            pathIdx = x
    if pathIdx:
        used = [-1]
        for x in range(len(section[pathIdx])):
            num = section[pathIdx][x]
            if num in used:
                continue
            used.append(num)
            svg += pthStr(num, frameLookup['p'][num]) + '\n'
    svg += '</defs>\n'

    for i in range(len(section[0])):
        svg += '<use x="' + str(frameLookup['x'][section[1][i]]) + '" y="' + str(frameLookup['y'][section[2][i]]) + '" xlink:href="#Image' + str(section[0][i]) + '" />\n'

    for i in range(len(section[3])):
        svg += txtStr(key, i, frameNo)

    svg += '</svg>'

    return svg


parse(sys.argv[1])
reshape()
SVGArr = []
for h in range(len(frameKey)):
    f = open("Frame" + str(h) + ".svg", 'w')
    f.write(toSVG(h))
    f.close()
