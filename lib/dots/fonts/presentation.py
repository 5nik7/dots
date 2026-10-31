"""Fonts bindings for shared human output; data and native settings stay separate."""
from files.catalog import Presentation
import os
from config_values import value
from style_config import current
from resources import cells


def preference(key, fallback=None):
    return value('apps.fonts.'+key, fallback)


class FontPresentation(Presentation):
    def __init__(self, stream=None, *, terminal=None, wrap=True):
        if terminal is None and os.environ.get('DOTS_MENU_CAPTURE')=='1':terminal=True
        super().__init__(stream,terminal=terminal)
        self.wrap=wrap

    def _spans(self, spans, prefix='', prefix_code=None, *, continuation_prefix=None):
        width=self.width
        # Retain real pane width for column layout; only suppress line wrapping.
        if not self.wrap:self.width=max(width,cells(prefix)+sum(cells(self.clean(text)) for text,_ in spans))
        try:return super()._spans(spans,prefix,prefix_code,continuation_prefix=continuation_prefix)
        finally:self.width=width

    def preferences(self):
        if not hasattr(self,'_preferences'):self._preferences=current()
        return self._preferences

    def paint(self, text, code, *, preferences=None):
        if self.color and preferences is None:preferences=self.preferences()
        return super().paint(text,code,preferences=preferences)

    def style(self, role, fallback):
        prefs=self.preferences()
        return prefs.sgr('fonts.'+role, fallback=prefs.style(fallback,app='cli'),app='cli') if prefs else '39'

    def heading(self, title):
        if not self.human:return super().heading(title)
        spans=[]
        if title=='Fonts' and self.icons:
            prefs=self.preferences()
            spans.append((self.icon('menu.fonts','󰛖')+' ',prefs.sgr('icons.menu.fonts',app='cli') if prefs and prefs.style('icons.menu.fonts',app='cli') else self.style('heading','ui.heading')))
        self.heading_spans([*spans,(title,self.style('heading','ui.heading'))])

    def detail_spans(self, label, spans, **kwargs):
        if self.human:kwargs['label_code']=self.style('label','ui.label')
        return super().detail_spans(label,spans,**kwargs)

    def detail(self, label, text, code=None):
        if self.human and code is None:
            role={'ID':'identity','Name':'identity','Target':'identity','Selection':'identity',
                  'Version':'version','Latest':'version','Installed':'version','Stored':'version','Active':'version','Pinned':'version',
                  'Source':'source','Provider':'source','Ownership':'source','Provenance':'source',
                  'Face':'face','Variant':'face','Glyph':'glyph','Codepoint':'glyph'}.get(label)
            code=self.style(role,'ui.accent' if role in ('identity','version') else 'ui.foreground') if role else None
            if label in ('Status','Result','Notice','Reason'):
                status=str(text).casefold()
                if any(v in status for v in ('failed','error')):semantic='status.error'
                elif label in ('Notice','Reason') or any(v in status for v in ('unavailable','uninstalled','pending','warning','skip')):semantic='status.warning'
                elif any(v in status for v in ('complete','available','stored','downloaded','copied','inserted')):semantic='status.success'
                else:semantic='ui.muted'
                prefs=self.preferences();code=prefs.sgr(semantic,app='cli') if prefs else None
        return super().detail(label,text,code)


def diagnostic(message, stream=None):
    ui=FontPresentation(stream)
    # Keep the established one-line diagnostic for ordinary stderr redirection.
    if not ui.human:ui.emit('fonts: '+ui.clean(message));return
    ui.heading('Fonts');ui.detail('Error',message,'91')
