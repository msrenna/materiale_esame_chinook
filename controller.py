# ==============================================================================
# 7. UI/controller.py — PATTERN DI GESTIONE EVENTI (Flet)
# ==============================================================================
class Controller_ESEMPIO:
    def __init__(self, view, model):
        self._view = view
        self._model = model
        self._nodo_selezionato = None  # valore scelto da una dropdown

    # --------------------------------------------------------------------
    # 7.1 CREAZIONE DEL GRAFO DA UNA DROPDOWN (es. paese o genere) —
    #     validazione minima: basta controllare che qualcosa sia stato
    #     selezionato.
    # --------------------------------------------------------------------
    def handle_crea_grafo(self, e):
        self._view._txt_result.controls.clear()

        valore_scelto = self._view._dd_filtro.value
        if valore_scelto is None:
            self._view.create_alert("Seleziona un valore dal menu a tendina.")
            return

        try:
            self._model.costruisci_grafo_orientato(valore_scelto)
            self._view._txt_result.controls.append(ft.Text("Grafo correttamente creato."))
            self._view._txt_result.controls.append(ft.Text(f"Numero nodi: {self._model.getNumNodi()}"))
            self._view._txt_result.controls.append(ft.Text(f"Numero archi: {self._model.getNumEdges()}"))
            self._riempi_dropdown_nodi()
            self._view.update_page()
        except Exception as ex:
            self._view.create_alert(f"Errore nella creazione del grafo: {ex}")

    # --------------------------------------------------------------------
    # 7.2 CREAZIONE DEL GRAFO SENZA ALCUN INPUT UTENTE (quando il grafo si
    #     costruisce sempre uguale, da tutto il database, senza filtri —
    #     caso della Traccia B vista negli esami: il pulsante "Crea grafo"
    #     non richiede alcuna validazione preliminare).
    # --------------------------------------------------------------------
    def handle_crea_grafo_senza_filtri(self, e):
        try:
            self._model.costruisci_grafo_semplice()
            self._view._txt_result.controls.clear()
            self._view._txt_result.controls.append(ft.Text("Grafo correttamente creato."))
            self._view._txt_result.controls.append(ft.Text(f"Numero di nodi: {self._model.getNumNodi()}"))
            self._view._txt_result.controls.append(ft.Text(f"Numero di archi: {self._model.getNumEdges()}"))
            self._riempi_dropdown_nodi()
            self._view.update_page()
        except Exception as ex:
            self._view.create_alert(f"Errore nella creazione del grafo: {ex}")

    # --------------------------------------------------------------------
    # 7.3 VALIDAZIONE DI UN CAMPO NUMERICO INTERO POSITIVO (N) — pattern
    #     identico a quello già visto su IMDB_2, da ripetere ogni volta che
    #     il testo chiede "l'utente inserisce un valore intero N"
    # --------------------------------------------------------------------
    def _leggi_intero_positivo(self, text_field, nome_campo="N"):
        try:
            valore = int(text_field.value)
        except (ValueError, TypeError):
            self._view.create_alert(f"Inserisci un valore numerico valido per {nome_campo}.")
            return None
        if valore <= 0:
            self._view.create_alert(f"Inserisci un numero intero positivo per {nome_campo}.")
            return None
        return valore

    # --------------------------------------------------------------------
    # 7.4 RICERCA RICORSIVA + STAMPA RISULTATI IN LISTVIEW (schema completo,
    #     con lista ordinata alfabeticamente e dettagli per ciascun nodo)
    # --------------------------------------------------------------------
    def handle_trova_gruppo(self, e):
        self._view._txt_result.controls.clear()

        if self._model.getNumNodi() == 0:
            self._view.create_alert("Creare prima il grafo.")
            return
        if self._nodo_selezionato is None:
            self._view.create_alert("Seleziona un elemento dal menu a tendina.")
            return

        n = self._leggi_intero_positivo(self._view._txtInN, "N")
        if n is None:
            return

        try:
            migliore_lista, miglior_punteggio = self._model.get_gruppo_migliore(self._nodo_selezionato, n)

            if not migliore_lista:
                self._view._txt_result.controls.append(ft.Text("Nessuna soluzione trovata con i vincoli richiesti."))
                self._view.update_page()
                return

            lista_ordinata = sorted(migliore_lista, key=lambda x: str(x))

            self._view._txt_result.controls.append(ft.Text("Elementi selezionati:"))
            for elemento in lista_ordinata:
                self._view._txt_result.controls.append(ft.Text(f"  - {elemento}"))
            self._view._txt_result.controls.append(ft.Text(f"Totale elementi: {len(migliore_lista)}"))
            self._view._txt_result.controls.append(ft.Text(f"Punteggio della soluzione ottima: {miglior_punteggio}"))
            self._view.update_page()
        except Exception as ex:
            self._view.create_alert(f"Errore nella ricerca della soluzione: {ex}")

    # --------------------------------------------------------------------
    # 7.5 RIEMPIMENTO DINAMICO DI UNA DROPDOWN CON OGGETTI (non solo
    #     stringhe) — `data=` porta l'oggetto vero e proprio, `key=str(...)`
    #     è l'etichetta mostrata a video.
    # --------------------------------------------------------------------
    def _riempi_dropdown_nodi(self):
        self._view._dd_nodi.options.clear()
        tutti_i_nodi = self._model.getAllNodi()  # o self._model._graph.nodes
        opzioni = list(map(
            lambda nodo: ft.dropdown.Option(data=nodo, key=str(nodo), on_click=self._scegli_nodo),
            tutti_i_nodi
        ))
        self._view._dd_nodi.options = opzioni
        self._view.update_page()

    def _scegli_nodo(self, e):
        self._nodo_selezionato = e.control.data

    # --------------------------------------------------------------------
    # 7.6 RIEMPIMENTO DI UNA DROPDOWN CON SOLE STRINGHE (es. paesi, generi)
    #     — più semplice del 7.5, non serve on_click dedicato per ciascuna
    #     opzione: basta leggere .value della dropdown al momento del click
    #     sul pulsante (si veda handle_crea_grafo sopra).
    # --------------------------------------------------------------------
    def riempi_dropdown_stringhe(self):
        valori = self._model.getAllPaesi()  # o getAllGeneri(), ecc.
        for v in valori:
            self._view._dd_filtro.options.append(ft.dropdown.Option(v))
        self._view.update_page()

#===================================================================================
# CONTROLLER
#===================================================================================
# dropdown
def handle_(self, values):
    values = self._model.get_
    for value in values:
        self._view._dd_.options.append(ft.dropdown.Option(key=value., text=value., data=value, on_click=self.handle_dd_))
def handle_dd_(self, evento):
    self._dd_ = evento.control.data
    print(self._dd_)

self._view._txt_result.controls.clear()
if self._dd_ is None:
    self._view._txt_result.controls.clear()
    self._view._txt_result.controls.append(ft.Text("Selezionare .", color="red"))
    return

# text
self._view._txt_result.controls.clear()
if == '':
    self._view._txt_result.controls.clear()
    self._view.create_alert(ft.Text("Inserire .", color="red"))
    return
try:
    = int()
except ValueError:
    self._view.create_alert(ft.Text("Inserire un numero valido.", color="red"))
    return
if <= 0:
    self._view._txt_result.controls.clear()
    self._view._txt_result.controls.append(ft.Text("Inserire un numero valido.", color="red"))
    return

self._view._txt_result.controls.clear()
nodes_number, edges_number = self._model.build_graph()
self._view._txt_result.controls.append(ft.Text("Il grafo è stato creato correttamente.", color="green"))
self._view._txt_result.controls.append(ft.Text(f"Il grafo è costituito da {nodes_number} nodi e {edges_number} archi."))
self._view.update_page()

def handle_graph_details(self, evento):
    self._view._txt_result.controls.clear()
      = self._model.get_graph_details()
    # nodo di differenza di peso tra gli archi uscenti e gli archi entranti maggiore
    self._view._txt_result.controls.append(ft.Text(f"Il nodo avente differenza di peso tra gli archi entranti e gli archi uscenti maggiore è {best_node} con un peso di {best_weight}."))
    # x archi di differenza di preso tra  gli archi uscenti e gli archi entranti maggore in ordine di peso decrescente
    self._view._txt_result.controls.append(ft.Text("I nodi aventi differenza di pesotra gli archi entranti e gli archi uscenti maggiore sono:"))
    for i in range(min(len(best_nodes), )):
        self._view._txt_result.controls.append(ft.Text(f"{best_nodes[i][0].} - {best_nodes[i][1]}"))
    # x archi di peso maggiore in ordine di peso decrescente
    self._view._txt_result.controls.append(ft.Text("Gli archi aventi peso maggiore sono:"))
    for i in range(min(len(best_edges), )):
        self._view._txt_result.controls.append(ft.Text(f"{best_edges[i][0].} - {best_edges[i][1].} - {best_edges[i][2]["weight"]}"))
    self._view._txt_result.controls.append(ft.Text(f"Il numero di componenti connesse è {connected_components_number}."))
    # componente connessa di lunghezza maggiore
    self._view._txt_result.controls.append(ft.Text(f"I nodi della componente connessa di lunghezza maggiore sono:"))
    for node in best_connected_component:
        self._view._txt_result.controls.append(ft.Text(f"{node.}"))
    # componente connessa di lunghezza maggiore con i nodi in ordine di grado decrescente o in ordine di peso massimo decrescente
    self._view._txt_result.controls.append(ft.Text(f"I nodi della componente connessa di lunghezza maggiore sono:"))
    for node in best_connected_component:
        self._view._txt_result.controls.append(ft.Text(f"{node[0].} - {node[1]}"))
    self._view.update_page()

self._view._txt_result.controls.clear()
best_, best_ = self._model.get_()
self._view._txt_result.controls.append(ft.Text(f"{best_}"))
for node in best_:
    self._view._txt_result.controls.append(ft.Text(f"{node}"))
self._view.update_page()