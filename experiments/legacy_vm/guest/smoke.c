/* Self-authored, redistributable ARM926 guest. This is NOT iOS or Safari. MIT. */
typedef unsigned int u32;
typedef unsigned char u8;
#define MMIO(a) (*(volatile u32 *)(a))
#define W 640
#define H 480
static volatile u32 *fb = (volatile u32 *)0x01000000;
static void say(const char *s) {
    while (*s) {
        while (MMIO(0x101f1018) & 32) {}
        MMIO(0x101f1000) = (u8)*s++;
    }
}
static void box(int x, int y, int w, int h, u32 c) {
    for (int j=y;j<y+h;j++) for (int i=x;i<x+w;i++) fb[j*W+i]=c;
}
static const u8 *glyph(char c) {
    static const u8 a[]={14,17,17,31,17,17,17}, b[]={30,17,17,30,17,17,30};
    static const u8 cc[]={14,17,16,16,16,17,14}, e[]={31,16,16,30,16,16,31};
    static const u8 f[]={31,16,16,30,16,16,16}, g[]={14,17,16,23,17,17,15};
    static const u8 i[]={14,4,4,4,4,4,14}, k[]={17,18,20,24,20,18,17};
    static const u8 l[]={16,16,16,16,16,16,31}, m[]={17,27,21,21,17,17,17};
    static const u8 n[]={17,25,25,21,19,19,17}, o[]={14,17,17,17,17,17,14};
    static const u8 p[]={30,17,17,30,16,16,16}, r[]={30,17,17,30,20,18,17};
    static const u8 s[]={15,16,16,14,1,1,30}, t[]={31,4,4,4,4,4,4};
    static const u8 u[]={17,17,17,17,17,17,14}, v[]={17,17,17,17,17,10,4};
    static const u8 z[]={0,0,0,0,0,0,0};
    switch(c) {
        case 'A':return a; case 'B':return b; case 'C':return cc; case 'E':return e;
        case 'F':return f; case 'G':return g; case 'I':return i; case 'K':return k;
        case 'L':return l; case 'M':return m; case 'N':return n; case 'O':return o;
        case 'P':return p; case 'R':return r; case 'S':return s; case 'T':return t;
        case 'U':return u; case 'V':return v; default:return z;
    }
}
static void text(int x,int y,const char *s,int scale,u32 color) {
    for (;*s;s++,x+=6*scale) {
        const u8 *g=glyph(*s);
        for(int row=0;row<7;row++) for(int col=0;col<5;col++)
            if(g[row]&(1<<(4-col))) box(x+col*scale,y+row*scale,scale,scale,color);
    }
}
void guest_main(void) {
    box(0,0,W,H,0x0d1117);
    box(32,32,576,96,0x161b22);
    text(52,52,"ACCI VM",8,0x58a6ff);
    text(44,170,"ARM GUEST",5,0xe6edf3);
    text(44,225,"FRAMEBUFFER OK",4,0x3fb950);
    text(44,330,"INPUT",4,0x8b949e);
    box(240,320,340,64,0x30363d);
    MMIO(0x10120000)=((W/16-1)<<2);
    MMIO(0x10120004)=H-1;
    MMIO(0x10120008)=0;
    MMIO(0x10120010)=0x01000000;
    /* Versatile's PL110 swaps the control/interrupt-mask register offsets. */
    MMIO(0x10120018)=1|(5<<1)|(1<<5)|(1<<8)|(1<<11);
    MMIO(0x10006000)=4; /* enable the PL050 keyboard controller */
    say("ACCI_VM_BOOT_OK\n");
    int release = 0;
    for (;;) {
        if (MMIO(0x10006004)&16) {
            u32 key=MMIO(0x10006008);
            if (key == 0xf0) { release = 1; continue; }
            /* PS/2 set 2 A make code; ignore VNC modifier synchronization. */
            if(key==0x1c && !release) {
                box(240,320,340,64,0x123821);
                text(268,336,"OK",5,0x3fb950);
                say("ACCI_INPUT_OK\n");
            }
            release = 0;
        }
    }
}