; Four flat logical entrypoints; parent can assemble separately or as oneblock.
; Parent replaces CORE_SERVICE/END_SERVICE/FREESTATE_SERVICE and both saved-v2
; forward symbols. Forward symbols MUST point to saved pre-hook v2 host paths,
; not to guestDD5A0/DDDBB0, which would recurse through the new hook.

auto_update_hook:
    pushal
    mov ecx, esi
    call CORE_SERVICE
    popal
    mov ecx, esi
    pop esi
    jmp 0xddef3

auto_end_hook:
    pushal
    call END_SERVICE
    popal
    push ecx
    push esi
    mov esi, ecx
    jmp 0xdd9e4

auto_initialize_hook:
    pushal
    call FREESTATE_SERVICE
    popal
    jmp OLD_V2_INIT_FORWARD

auto_destroy_hook:
    pushal
    call FREESTATE_SERVICE
    popal
    jmp OLD_V2_DESTROY_FORWARD
