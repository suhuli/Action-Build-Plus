#!/usr/bin/env python3
"""Narrow, fail-closed SUSFS priority feature integration for builtin KSU.

--check plans changes without writing (safe during candidate selection).
--apply adds the real upstream Kconfig stanza and guards the existing real ioctl.
No function bodies/stubs or bypasses are manufactured. Not a full C preprocessor.
"""
import re
import sys
from pathlib import Path

FLAG='CONFIG_KSU_SUSFS_PRIORITY_UID_FILTER'
FUNC='susfs_set_priority_uid_filter'
CALL=re.compile(r'(?P<i>[ \t]*)case CMD_SUSFS_SET_PRIORITY_UID_FILTER:\n(?P=i)[ \t]+susfs_set_priority_uid_filter\(arg\);\n(?P=i)[ \t]+return 0;')

def plan(susfs,ksu):
    susfs,ksu=Path(susfs),Path(ksu)
    fs=(susfs/'fs/susfs.c').read_text()
    header=(susfs/'include/linux/susfs.h').read_text()
    files=list(ksu.rglob('*.c'))
    callers=[p for p in files if re.search(r'\b'+FUNC+r'\s*\(',p.read_text())]
    if not callers:
        return {}  # BakaSU has no dispatcher for this feature; do not claim to add it.
    guarded=('#ifdef '+FLAG) in header
    if not guarded:
        return {}  # Explicit legacy SUSFS keeps its original contract.
    if '#ifdef '+FLAG not in fs:
        raise ValueError('priority feature header/implementation guards do not agree')
    if len(callers)!=1:
        raise ValueError('unknown priority dispatcher layout; manual review required')
    p=callers[0]; code=p.read_text();m=CALL.search(code)
    if not m or len(CALL.findall(code))!=1 or len(re.findall(r'\b'+FUNC+r'\s*\(',code))!=1:
        raise ValueError('expected one audited priority ioctl block')
    changes={}
    # Accept only the exact guard around the known block, not unrelated #ifdefs.
    wrapped='#ifdef '+FLAG+'\n'+m.group(0)+'\n#endif // '+FLAG
    if not re.search(r'#ifdef '+FLAG+r'\n'+re.escape(m.group(0))+r'\n#endif(?:[^\n]*)',code):
        changes[p]=code[:m.start()]+wrapped+code[m.end():]
    kconfig=ksu/'Kconfig';kc=kconfig.read_text()
    if not re.search(r'^config KSU_SUSFS_PRIORITY_UID_FILTER$',kc,re.M):
        upstream=(susfs/'KernelSU/10_enable_susfs_for_ksu.patch').read_text()
        added='\n'.join(l[1:] for l in upstream.splitlines() if l.startswith('+') and not l.startswith('+++'))+'\n'
        stanza=re.search(r'^config KSU_SUSFS_PRIORITY_UID_FILTER\n.*?(?=^config |^endmenu)',added,re.M|re.S)
        if not stanza or 'depends on KSU_SUSFS' not in stanza.group() or 'default y' not in stanza.group():
            raise ValueError('selected SUSFS has no reviewed upstream priority Kconfig stanza')
        anchor='config KSU_SUSFS_SUS_MAP\n'
        if kc.count(anchor)!=1:raise ValueError('unknown Kconfig insertion point')
        changes[kconfig]=kc.replace(anchor,stanza.group().rstrip()+'\n\n'+anchor,1)
    else:
        stanzas=re.findall(r'^config KSU_SUSFS_PRIORITY_UID_FILTER\n.*?(?=^config |^endmenu|\Z)',kc,re.M|re.S)
        if len(stanzas)!=1 or not all(re.search(pattern,stanzas[0],re.M) for pattern in
                (r'^\s+bool\b',r'^\s+depends on KSU_SUSFS\s*$',r'^\s+default y\s*$')):
            raise ValueError('existing priority Kconfig stanza does not match the reviewed feature contract')
    observer=ksu/'manager/pkg_observer.c'
    if observer.exists():
        original=observer.read_text(); updated=original
        pattern=re.compile(r'^[ \t]*susfs_parse_priority_app_strings\(\);',re.M)
        for call in reversed(list(pattern.finditer(original))):
            block=call.group()
            before=original[:call.start()].rstrip()
            after=original[call.end():].lstrip()
            if before.endswith('#ifdef '+FLAG) and after.startswith('#endif'):
                continue
            updated=updated[:call.start()]+'#ifdef '+FLAG+'\n'+block+'\n#endif // '+FLAG+updated[call.end():]
        if updated!=original:changes[observer]=updated
    # Match the actual selected implementation's third argument width (LTO ABI).
    sepolicy=ksu/'selinux/sepolicy.c'
    if sepolicy.exists():
        old=sepolicy.read_text()
        decl='extern int susfs_add_sus_avd_allowed_by_type(u32 s_type, u32 t_type, u16 type, u32 orig_avd_allowed);'
        if decl in old:
            if not re.search(r'int susfs_add_sus_avd_allowed_by_type\(u32 s_type, u32 t_type, u32 c_type, u32 orig_avd_allowed\)',fs):
                raise ValueError('unknown SUSFS av-rule implementation signature')
            changes[sepolicy]=old.replace(decl,decl.replace('u16 type','u32 type'),1)
    return changes

if __name__=='__main__':
    if len(sys.argv)!=4 or sys.argv[1] not in ('--check','--apply'):
        sys.exit('usage: susfs_feature_compat.py --check|--apply <kernel_patches> <KernelSU/kernel>')
    try:
        changes=plan(sys.argv[2],sys.argv[3])
        if sys.argv[1]=='--apply':
            for path,text in changes.items():path.write_text(text)
        print(('Planned' if sys.argv[1]=='--check' else 'Applied')+' SUSFS feature compatibility: '+', '.join(str(p) for p in changes))
    except (OSError,ValueError) as e:
        sys.exit('::error title=SUSFS feature contract::'+str(e))
