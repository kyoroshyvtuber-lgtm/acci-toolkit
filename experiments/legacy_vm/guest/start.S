.syntax unified
.cpu arm926ej-s
.arm
.section .text.boot
.global _start
_start:
    ldr sp, =0x03fff000
    bl guest_main
1:  b 1b