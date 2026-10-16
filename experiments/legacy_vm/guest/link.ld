ENTRY(_start)
SECTIONS {
  . = 0x10000;
  .text : { *(.text.boot) *(.text*) }
  .rodata : { *(.rodata*) }
  .data : { *(.data*) }
  .bss : { *(.bss*) *(COMMON) }
  /DISCARD/ : { *(.comment) *(.ARM.exidx*) *(.ARM.extab*) }
}