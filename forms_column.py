"""
forms_column.py - Formularze KOLUMNY (Faza 7).

Wczytuje zaprojektowane w Qt Designerze pliki .ui 1:1 (rozstaw, proporcje, format):
  - edit    -> Formularz_Edytor_Kolumny.ui
  - preview -> Formularz_Hover_kolumny.ui

Pola wyboru (rozwijane listy) na formularzu edycji:
  - header_line1            (Typ/Sposob      -> Name_proces)
  - header_line2a           (Obrabiarka      -> name_machine)
  - worker_1_worker_2name   (Nazwisko worker_1)
  - worker_2_worker_2name   (Nazwisko worker_2)

Dwie linie pracownika wybierane radiobuttonami:
  - worker_1  -> worker_1_worker_1name, worker_1_worker_2name,
                 worker_1_id_worker,     worker_1_spec_worker
  - worker_2  -> worker_2_worker_1name, worker_2_worker_2name,
                 worker_2_id_worker,     worker_2_spec_worker
Dane z wybranej linii trafiaja na pasek kolumny (header_line2):
  - TylkoNrewid odznaczony -> "Imie Nazwisko" (bez id_worker)
  - TylkoNrewid zaznaczony -> tylko id_worker
Autouzupelnianie: wybor pracownika/maszyny/stanowiska uzupelnia pozostale pola
(Nazwisko, Spec, Il.zm, Kod, Tj.Tech, Nr.stan - informacyjne).
"""
import os

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QPushButton, QComboBox

from modules.ui import form_style as fs
from modules.reference.managers.pracownicy_manager import PracownicyManager
from modules.reference.managers.maszyny_manager import MaszynyManager
from modules.reference.managers.kody_manager import KodyManager


def _ui_file(name):
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "assets", "ui_files", name)


def _combobox(dialog, name):
    """Zamienia QLineEdit z .ui na QComboBox w tym samym polozeniu (te same wymiary)."""
    edit = getattr(dialog, name)
    combo = QComboBox(dialog)
    combo.setGeometry(edit.geometry())
    combo.setFont(edit.font())
    combo.setStyleSheet(edit.styleSheet())
    combo.setEditable(True)
    combo.setFocusPolicy(edit.focusPolicy())
    edit.setParent(None)
    edit.deleteLater()
    setattr(dialog, name, combo)
    return combo


class ColumnEditDialog(QDialog):
    """Edycja kolumny - loadUi(Formularz_Edytor_Kolumny.ui) 1:1."""

    def __init__(self, column, mode="edit", view=None):
        super().__init__(view)
        self.column = column
        self.mode = mode
        uic.loadUi(_ui_file("Formularz_Edytor_Kolumny.ui"), self)
        self.setModal(True)
        self.setFixedSize(self.width(), self.height())
        self._loading = False
        self._build_combos()
        self._load_values()
        self._apply_style()

        # --- przyciski cykliczne (Kol.Belki / Stanow.) ---
        self.header_overlay.clicked.connect(self._on_header_overlay)
        self.body_overlay_.clicked.connect(self._on_body_overlay)
        self.Zamyka_edycje.clicked.connect(self._apply_and_close)

    # --- budowa pol wyboru ---

    def _build_combos(self):
        self.combo_typ = _combobox(self, "header_line1")
        self.combo_obrabiarka = _combobox(self, "header_line2a")
        self.combo_nazwisko1 = _combobox(self, "worker_1_worker_2name")
        self.combo_nazwisko2 = _combobox(self, "worker_2_worker_2name")

        self._kody = KodyManager().list_all()
        self._maszyny = MaszynyManager().list_all()
        self._pracownicy = PracownicyManager().list_all()

        typ_items = sorted({k["name_proces"] for k in self._kody if k.get("name_proces")})
        obr_items = sorted({m["name_machine"] for m in self._maszyny if m.get("name_machine")})
        nazw_items = sorted({p["worker_2name"] for p in self._pracownicy if p.get("worker_2name")})

        self.combo_typ.addItems(typ_items)
        self.combo_obrabiarka.addItems(obr_items)
        self.combo_nazwisko1.addItems(nazw_items)
        self.combo_nazwisko2.addItems(nazw_items)

        # Autouzupelnianie (zabezpieczenie przed petlami przez _loading).
        self.combo_typ.currentTextChanged.connect(self._on_typ_changed)
        self.combo_obrabiarka.currentTextChanged.connect(self._on_obrabiarka_changed)
        self.combo_nazwisko1.currentTextChanged.connect(lambda t: self._autocomplete_row(1, "nazwisko"))
        self.combo_nazwisko2.currentTextChanged.connect(lambda t: self._autocomplete_row(2, "nazwisko"))
        self.worker_1_worker_1name.textChanged.connect(lambda t: self._autocomplete_row(1, "imie"))
        self.worker_1_id_worker.textChanged.connect(lambda t: self._autocomplete_row(1, "id"))
        self.worker_2_worker_1name.textChanged.connect(lambda t: self._autocomplete_row(2, "imie"))
        self.worker_2_id_worker.textChanged.connect(lambda t: self._autocomplete_row(2, "id"))

    # --- ladowanie / zapis ---

    def _load_values(self):
        self._loading = True
        try:
            col = self.column
            self._set_combo(self.combo_typ, col.header_line1.toPlainText())
            self._set_combo(self.combo_obrabiarka, col.header_line2a.toPlainText())

            # Wybor linii (worker_1 / worker_2) i RODO (TylkoNrewid) - z zapisu.
            if self._has_worker_radios():
                sel = getattr(col, "worker_sel", 1)
                self.worker_1.setChecked(sel != 2)
                self.worker_2.setChecked(sel == 2)
                self.TylkoNrewid.setChecked(getattr(col, "tylko_nr", False))

            self._load_row_values(1, col)
            self._load_row_values(2, col)

            # Na pasku kolumny header_line3 to Nr.stan (Id_machine) - do pola 'Nr.stan'.
            self.lineEdit_22.setText(col.header_line3.toPlainText())

            # 'Opis' (tylko_dla_form) - pole informacyjne (col.opis, hover).
            self.tylko_dla_form.setText(getattr(col, "opis", ""))
        finally:
            self._loading = False
        self._init_worker_selection()
        self._sync_informational()

    def _load_row_values(self, which, col):
        imie_w, naz_w, id_w, spec_w = self._row_widgets(which)
        if which == 2:
            imie_w.setText(getattr(col, "w2_imie", ""))
            self._set_combo(naz_w, getattr(col, "w2_nazwisko", ""))
            id_w.setText(getattr(col, "w2_id", ""))
            spec_w.setText(getattr(col, "w2_spec", ""))
        else:
            imie_w.setText(getattr(col, "w1_imie", ""))
            self._set_combo(naz_w, getattr(col, "w1_nazwisko", ""))
            id_w.setText(getattr(col, "w1_id", ""))
            spec_w.setText(getattr(col, "w1_spec", ""))

    def _set_combo(self, combo, value):
        if value and combo.findText(value) == -1:
            combo.addItem(value)
        if value:
            combo.setCurrentText(value)
        elif combo.count():
            combo.setCurrentIndex(-1)

    def _apply(self):
        col = self.column
        col.header_line1.setPlainText(self.combo_typ.currentText())
        col.header_line2a.setPlainText(self.combo_obrabiarka.currentText())

        # Dane obu linii pracownika - trwale.
        col.w1_imie, col.w1_nazwisko, col.w1_id, col.w1_spec = self._row_fields(1)
        col.w2_imie, col.w2_nazwisko, col.w2_id, col.w2_spec = self._row_fields(2)

        if self._has_worker_radios():
            col.worker_sel = 2 if self.worker_2.isChecked() else 1
            col.tylko_nr = self.TylkoNrewid.isChecked()
            fields = self._selected_fields()
        else:
            fields = {"imie": "", "nazwisko": "", "id": "", "spec": ""}
        # Pasek kolumny: "Imie Nazwisko" albo (TylkoNrewid) tylko id_worker.
        col.header_line2.setPlainText(self._column_worker_text(fields))
        # Na pasku kolumny header_line3 = Nr.stan (Id_machine).
        col.header_line3.setPlainText(self.lineEdit_22.text().strip())
        # 'Opis' (tylko_dla_form) - informacyjny (col.opis, hover), nie notatnik.
        col.opis = self.tylko_dla_form.text()
        col.update()

    def _apply_and_close(self):
        self._apply()
        self.accept()

    # --- linie pracownika (worker_1 / worker_2) ---

    def _row_widgets(self, which):
        if which == 2:
            return (self.worker_2_worker_1name, self.combo_nazwisko2,
                    self.worker_2_id_worker, self.worker_2_spec_worker)
        return (self.worker_1_worker_1name, self.combo_nazwisko1,
                self.worker_1_id_worker, self.worker_1_spec_worker)

    def _row_fields(self, which):
        imie_w, naz_w, id_w, spec_w = self._row_widgets(which)
        naz = naz_w.currentText().strip() if isinstance(naz_w, QComboBox) else naz_w.text().strip()
        return (imie_w.text().strip(), naz, id_w.text().strip(), spec_w.text().strip())

    def _has_worker_radios(self):
        return all(hasattr(self, n) for n in ("worker_1", "worker_2", "TylkoNrewid"))

    def _selected_which(self):
        if self._has_worker_radios() and self.worker_2.isChecked():
            return 2
        return 1

    def _selected_fields(self):
        imie, nazwisko, nr, spec = self._row_fields(self._selected_which())
        return {"imie": imie, "nazwisko": nazwisko, "id": nr, "spec": spec}

    def _column_worker_text(self, fields):
        """Tekst na kolumnie (header_line2): 'Imie Nazwisko' (bez id_worker),
        a przy zaznaczonym TylkoNrewid sam id_worker."""
        if self._has_worker_radios() and self.TylkoNrewid.isChecked():
            return fields["id"]
        return (fields["imie"] + " " + fields["nazwisko"]).strip()

    def _init_worker_selection(self):
        if not self._has_worker_radios():
            return
        self.worker_1.toggled.connect(self._on_worker_selection)
        self.worker_2.toggled.connect(self._on_worker_selection)
        self.TylkoNrewid.stateChanged.connect(self._on_worker_selection)

    def _on_worker_selection(self, *_):
        if self._loading:
            return
        self.column.header_line2.setPlainText(self._column_worker_text(self._selected_fields()))
        self.column.update()

    # --- autouzupelnianie ---

    def _find_worker(self, fields, prefer):
        keys = [prefer, "id", "imie", "nazwisko"]
        seen = set()
        for k in keys:
            if k in seen or not fields.get(k):
                continue
            seen.add(k)
            if k == "id":
                w = next((p for p in self._pracownicy if p.get("id_worker") == fields[k]), None)
            elif k == "imie":
                w = next((p for p in self._pracownicy if p.get("worker_1name") == fields[k]), None)
            else:
                w = next((p for p in self._pracownicy if p.get("worker_2name") == fields[k]), None)
            if w is not None:
                return w
        return None

    def _autocomplete_row(self, which, trigger):
        if self._loading:
            return
        imie_w, naz_w, id_w, spec_w = self._row_widgets(which)
        imie, nazwisko, nr, spec = self._row_fields(which)
        worker = self._find_worker({"imie": imie, "nazwisko": nazwisko, "id": nr}, trigger)
        self._loading = True
        try:
            if worker is not None:
                if trigger != "imie" and worker.get("worker_1name"):
                    imie_w.setText(worker["worker_1name"])
                if trigger != "nazwisko" and worker.get("worker_2name"):
                    self._set_combo(naz_w, worker["worker_2name"])
                if trigger != "id" and worker.get("id_worker"):
                    id_w.setText(worker["id_worker"])
                if worker.get("spec_worker"):
                    spec_w.setText(worker["spec_worker"])
        finally:
            self._loading = False
        self._sync_informational()

    def _sync_informational(self):
        """Wypelnia tylko pola INFORMACYJNE (Il.zm, Kod, Tj.Tech, Nr.stan).

        Nie nadpisuje pol pracownika (Imie, Nazwisko, Nr.ewid, Spec) - te sa
        recznie edytowalne; autouzupelnianie robi _autocomplete_row()."""
        if self._loading:
            return
        self._loading = True
        try:
            fields = self._selected_fields()
            worker = self._find_worker(fields, "id")
            if worker is not None:
                self.Nowa_zmien.setText(worker.get("time_work", ""))

            typ = self.combo_typ.currentText()
            kod = next((k for k in self._kody if k.get("name_proces") == typ), None)
            if kod is not None and hasattr(self, 'Nowa_zmien_2'):
                self.Nowa_zmien_2.setText(kod.get("code_process", ""))

            # Nr.stan (lineEdit_22) = id_machine (z bazy maszyn).
            maszyna = self._find_maszyna(typ)
            if maszyna is not None:
                self.lineEdit_22.setText(maszyna.get("id_machine", ""))
                if maszyna.get("name_proces"):
                    self.combo_typ.setCurrentText(maszyna["name_proces"])
        finally:
            self._loading = False

    def _find_maszyna(self, name_proces=""):
        """Maszyna dla 'Nr.stan' (id_machine): najpierw po obrabiarce, potem po typie."""
        obr = self.combo_obrabiarka.currentText()
        m = next((x for x in self._maszyny if x.get("name_machine") == obr), None)
        if m is None:
            m = next((x for x in self._maszyny if x.get("name_proces") == name_proces), None)
        return m

    def _on_typ_changed(self, text):
        if self._loading:
            return
        # Kod procesu z bazy KODOW.
        kod = next((k for k in self._kody if k.get("name_proces") == text), None)
        if kod is not None and hasattr(self, 'Nowa_zmien_2'):
            self.Nowa_zmien_2.setText(kod.get("code_process", ""))
        self._sync_informational()

    def _on_obrabiarka_changed(self, text):
        if self._loading:
            return
        maszyna = next((m for m in self._maszyny if m.get("name_machine") == text), None)
        if maszyna is not None and maszyna.get("name_proces"):
            self.combo_typ.setCurrentText(maszyna["name_proces"])
        self._sync_informational()

    # --- cykliczne overlaya ---

    def _on_header_overlay(self):
        col = self.column
        col.header_overlay_index = (col.header_overlay_index + 1) % col._header_overlays_count()
        col.update_header_overlay()
        col.update()

    def _on_body_overlay(self):
        col = self.column
        col.body_overlay_index = (col.body_overlay_index + 1) % col._body_overlays_count()
        col.update_body_overlay()
        col.update()

    def _apply_style(self):
        self.setStyleSheet(fs.dialog_stylesheet())
        for btn in self.findChildren(QPushButton):
            btn.setStyleSheet(fs.button_stylesheet("small"))


class ColumnHoverDialog(QDialog):
    """Podglad kolumny (Hover) - loadUi(Formularz_Hover_kolumny.ui) 1:1."""

    def __init__(self, column, mode="preview", view=None):
        super().__init__(view)
        self.column = column
        self.mode = mode
        uic.loadUi(_ui_file("Formularz_Hover_kolumny.ui"), self)
        self.setModal(True)
        self.setFixedSize(self.width(), self.height())
        self._apply_style()
        self._fill_values()

        self.Zamyka_edycje.clicked.connect(self.accept)
        self.notes_kolumny.clicked.connect(self._open_notes)
        self.pushButton_4.clicked.connect(self._link)
        self.pushButton_6.clicked.connect(self._unlink)

    def _fill_values(self):
        col = self.column
        sel = getattr(col, "worker_sel", 1)
        imie = getattr(col, "w1_imie", "") if sel != 2 else getattr(col, "w2_imie", "")
        nazwisko = getattr(col, "w1_nazwisko", "") if sel != 2 else getattr(col, "w2_nazwisko", "")
        nr = getattr(col, "w1_id", "") if sel != 2 else getattr(col, "w2_id", "")

        self.label_2.setText(col.header_line1.toPlainText())          # Typ/Sposob
        self.selftext_items3_8.setText(col.header_line2a.toPlainText())  # Obrabiarka
        self.selftext_items1_3.setText(getattr(col, "opis", ""))      # Opis (informacyjny)
        self.selftext_items3_7.setText(col.header_line3.toPlainText())  # Nr.stan (Id_machine)
        # Operator: przy TylkoNrewid Imie i Nazwisko NIE sa wyswietlane.
        if getattr(col, "tylko_nr", False):
            self.selftext_items3_6.setText("")
        else:
            self.selftext_items3_6.setText((imie + " " + nazwisko).strip())
        self.wpis_nrprac.setText(nr)                                  # Nr.ewid (Id_worker)

    def _open_notes(self):
        from modules.ui.forms_card import CardNotesDialog

        def on_change(text):
            # Notes nie trafia do linii 'Opis' w hoverze kolumny (linia informacyjna).
            self.column.notes = text
            self.column.update_info_icon()
            self.column.update()

        self._notes_dialog = CardNotesDialog(
            parent=self, text=self.column.notes, on_save=on_change, on_change=on_change,
            title="Notes Kolumny", auto_line2="Notes Kolumny:   ", live=True
        )
        self._position_child(self._notes_dialog, from_right=True)
        self._notes_dialog.show()

    def _position_child(self, dialog, from_right):
        """Ustawia okno 5px od krawedzi hovera, wyrównane górą."""
        gap = 5
        if from_right:
            x = self.x() + self.width() + gap
        else:
            x = self.x() - dialog.width() - gap
        dialog.move(x, self.y())

    def _link(self):
        table = self.column.parent_table
        if table is not None and hasattr(table, "link_column"):
            table.link_column(self.column)

    def _unlink(self):
        table = self.column.parent_table
        if table is not None and hasattr(table, "unlink_column"):
            table.unlink_column(self.column)

    def _apply_style(self):
        self.setStyleSheet(fs.dialog_stylesheet())
        for btn in self.findChildren(QPushButton):
            btn.setStyleSheet(fs.button_stylesheet("small"))