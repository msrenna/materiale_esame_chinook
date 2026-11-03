"""
Promemoria schema Chinook (colonne principali, attenzione al CamelCase le colonne iniziano con la MAIUSCOLA):
  Artist(ArtistId, Name)
  Album(AlbumId, Title, ArtistId) -- FK -> Artist
  Track(TrackId, Name, AlbumId, MediaTypeId, GenreId, Composer, Milliseconds, Bytes, UnitPrice) -- FK -> Album, MediaType, Genre
  Genre(GenreId, Name)
  MediaType(MediaTypeId, Name)
  Playlist(PlaylistId, Name)
  PlaylistTrack(PlaylistId, TrackId) -- tabella ponte Playlist <-> Track
  Customer(CustomerId, FirstName, LastName, Company, Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId)
  Invoice(InvoiceId, CustomerId, InvoiceDate, BillingAddress, ..., Total) -- FK -> Customer
  InvoiceLine(InvoiceLineId, InvoiceId, TrackId, UnitPrice, Quantity)  -- FK -> Invoice, Track
  Employee(EmployeeId, LastName, FirstName, Title, ReportsTo, ...)

Catena tipica per andare "da un artista/genere fino a cosa ha comprato un cliente": 
Artist -> Album -> Track -> InvoiceLine -> Invoice -> Customer\-> PlaylistTrack -> Playlist\-> Genre
"""
# ==============================================================================
# 0. IMPORT TIPICI
# ==============================================================================
# nel DAO:
from database.DB_connect import DBConnect
# nel model:
import copy
import itertools
from collections import defaultdict
import networkx as nx
from database.DAO import DAO
# per le dataclass dei "nodi" del grafo:
from dataclasses import dataclass, field
# nel controller/view:
import flet as ft

# ==============================================================================
# 3. model/<oggetto>.py — DATACLASS PER I NODI DEL GRAFO
# ==============================================================================
# Stesse regole già viste per IMDB_2: un nodo del grafo deve essere SEMPRE
# hashable e confrontabile (basta farlo sul solo id univoco), per poter
# essere usato come nodo di networkx e come chiave in set/dict. __str__
# serve per farlo comparire leggibile nella ListView.
#
# ATTENZIONE ALLE MAIUSCOLE: a differenza di IMDB_2 (colonne minuscole:
# id, name, movie_id...), le colonne di Chinook sono in CamelCase
# (CustomerId, ArtistId, Title...). Se si vuole usare la scorciatoia
# Classe(**row) per costruire l'oggetto direttamente dal risultato della
# query, i campi della dataclass DEVONO chiamarsi ESATTAMENTE come le
# colonne/alias della query (maiuscole comprese).

@dataclass
class Cliente_ESEMPIO:
    # Nota: qui i campi ricalcano l'intera tabella Customer (perché la
    # query usa "c.*"), più un campo aggiuntivo calcolato (Fatturato, da un
    # alias SQL — vedi sezione 2.2). Negli esami capita spesso di dover
    # mappare così TUTTE le colonne di una tabella, non solo un sottoinsieme.
    CustomerId: int
    FirstName: str
    LastName: str
    Company: str
    Address: str
    City: str
    State: str
    Country: str
    PostalCode: str
    Phone: str
    Fax: str
    Email: str
    SupportRepId: int
    Fatturato: float  # campo "aggiuntivo", popolato dalla query con SUM(i.Total) AS Fatturato

    def __hash__(self):
        return hash(self.CustomerId)

    def __eq__(self, other):
        if not isinstance(other, Cliente_ESEMPIO):
            return False
        return self.CustomerId == other.CustomerId

    def __str__(self):
        return f"{self.FirstName} {self.LastName} ({self.Country})"


@dataclass
class Track_ESEMPIO:
    TrackId: int
    Name: str
    AlbumId: int
    MediaTypeId: int
    GenreId: int
    Composer: str
    Milliseconds: int
    Bytes: int
    UnitPrice: float

    def __hash__(self):
        return hash(self.TrackId)

    def __eq__(self, other):
        if not isinstance(other, Track_ESEMPIO):
            return False
        return self.TrackId == other.TrackId

    def __str__(self):
        return f"{self.Name}"


@dataclass
class Album_ESEMPIO:
    AlbumId: int
    Title: str
    ArtistId: int
    # dati "pesanti" popolati in un secondo momento da un metodo DAO dedicato
    # (field(default_factory=list), MAI una lista mutabile come default diretto!)
    Tracks: list = field(default_factory=list)

    def __hash__(self):
        return hash(self.AlbumId)

    def __eq__(self, other):
        if not isinstance(other, Album_ESEMPIO):
            return False
        return self.AlbumId == other.AlbumId

    def __str__(self):
        return f"{self.Title}"

    def get_numero_tracce(self):
        return len(self.Tracks)


@dataclass
class Artista_ESEMPIO:
    ArtistId: int
    Name: str
    Tracks: list = field(default_factory=list)   # id (o oggetti) dei brani dell'artista
    Playlists: set = field(default_factory=set)  # id delle playlist in cui compare

    def __hash__(self):
        return hash(self.ArtistId)

    def __eq__(self, other):
        if not isinstance(other, Artista_ESEMPIO):
            return False
        return self.ArtistId == other.ArtistId

    def __str__(self):
        return f"{self.Name}"

    def get_numero_tracce(self):
        return len(self.Tracks)

    def get_numero_playlist(self):
        return len(self.Playlists)

# ==============================================================================
# 6. ALGORITMI RICORSIVI DI BACKTRACKING — PATTERN GENERALI
# ==============================================================================
class Ricorsione_ESEMPI(Model_ESEMPIO):

    # --------------------------------------------------------------------
    # 6.1 "GRUPPO" DI N NODI ADIACENTI (con vincoli sugli archi), che
    #     massimizza un punteggio calcolato sull'intero gruppo (qui: numero
    #     complessivo di brani). Identico, a parte i nomi, al pattern già
    #     visto per IMDB_2: ogni candidato deve essere adiacente ad almeno
    #     un nodo già scelto, e non deve esistere un arco di peso 1 verso
    #     nessuno dei nodi già presenti.
    # --------------------------------------------------------------------
    def get_gruppo_migliore(self, nodo_iniziale, n):
        if nodo_iniziale not in self._graph.nodes:
            return [], 0

        self._best_lista = []
        self._best_punteggio = 0

        parziale = [nodo_iniziale]
        self._ricorsione_gruppo(parziale, n)

        return self._best_lista, self._best_punteggio

    def _ricorsione_gruppo(self, parziale, n):
        if len(parziale) == n:
            punteggio = self._punteggio_gruppo(parziale)
            if punteggio > self._best_punteggio:
                self._best_punteggio = punteggio
                self._best_lista = copy.deepcopy(parziale)
            return

        for candidato in self._graph.nodes:
            if candidato in parziale:
                continue

            adiacente = any(self._graph.has_edge(candidato, esistente) for esistente in parziale)
            if not adiacente:
                continue

            # vincolo specifico dell'esame (qui: niente archi di peso 1
            # verso nodi già selezionati) — adattare la condizione al testo!
            vietato = any(
                self._graph.has_edge(candidato, esistente)
                and self._graph[candidato][esistente]["weight"] == 1
                for esistente in parziale
            )
            if vietato:
                continue

            parziale.append(candidato)
            self._ricorsione_gruppo(parziale, n)
            parziale.pop()

    def _punteggio_gruppo(self, nodi):
        return sum(nodo.get_numero_tracce() for nodo in nodi)

    # --------------------------------------------------------------------
    # 6.2 SELEZIONE DI N NODI, UNO PER OGNI COMPONENTE CONNESSA DISTINTA
    #     (schema "a scelta binaria": includi/scarta la componente
    #     corrente), col primo nodo imposto dall'utente e la sua
    #     componente esclusa dalla scelta per gli altri N-1. Variante vista
    #     in una soluzione ufficiale: le componenti rimanenti sono tenute
    #     in una LISTA (non generator) e PRUNATE man mano con `.remove()`
    #     oppure con lo slicing `[1:]` passato alla chiamata ricorsiva
    #     successiva (i due modi sono equivalenti: lo slicing crea una
    #     nuova lista senza il primo elemento, più sicuro di `.remove()`
    #     se si deve anche fare backtracking esplicito).
    # --------------------------------------------------------------------
    def get_selezione_migliore(self, nodo_iniziale, n):
        if nodo_iniziale not in self._graph.nodes:
            return [], 0

        componente_iniziale = self.get_componente_del_nodo(nodo_iniziale)
        if componente_iniziale is None:
            return [], 0

        tutte_componenti = list(nx.connected_components(self._graph))
        componenti_rimanenti = [c for c in tutte_componenti if c != componente_iniziale]

        self._best_lista = []
        self._best_punteggio = 0

        parziale = [nodo_iniziale]
        self._ricorsione_selezione(parziale, n, componenti_rimanenti)

        return self._best_lista, self._best_punteggio

    def _ricorsione_selezione(self, parziale, n, componenti_rimanenti):
        # --- condizione di terminazione: soluzione completa ---
        if len(parziale) == n:
            punteggio = self._punteggio_selezione(parziale)
            if punteggio > self._best_punteggio:
                self._best_punteggio = punteggio
                self._best_lista = copy.deepcopy(parziale)
            return

        # --- PRUNING: se non restano abbastanza componenti per arrivare a
        #     n elementi, interrompo subito questo ramo ---
        if not componenti_rimanenti or n - len(parziale) > len(componenti_rimanenti):
            return

        prossima_componente = componenti_rimanenti[0]

        # opzione 1: NON prendo nessun nodo da questa componente
        self._ricorsione_selezione(parziale, n, componenti_rimanenti[1:])

        # opzione 2: prendo il "migliore" nodo di questa componente (qui:
        # quello col maggior numero di tracce — adattare il criterio)
        migliore_della_componente = self._nodo_migliore_in(prossima_componente)
        if migliore_della_componente is not None:
            parziale.append(migliore_della_componente)
            self._ricorsione_selezione(parziale, n, componenti_rimanenti[1:])
            parziale.pop()

    def _nodo_migliore_in(self, nodi):
        migliore = None
        max_valore = 0
        for nodo in nodi:
            valore = nodo.get_numero_tracce()
            if valore > max_valore:
                max_valore = valore
                migliore = nodo
        return migliore

    def _punteggio_selezione(self, nodi):
        return sum(nodo.get_numero_tracce() for nodo in nodi)

    # --------------------------------------------------------------------
    # 6.3 CAMMINO SEMPLICE DI LUNGHEZZA MASSIMA, A PARTIRE DA UN NODO DATO,
    #     CON VINCOLO SU UN ATTRIBUTO DEL NODO NON STRETTAMENTE DECRESCENTE
    #     (qui: fatturato che non deve MAI aumentare lungo il cammino, cioè
    #     <= rispetto al nodo precedente — attenzione: non è "strettamente
    #     decrescente", il testo può ammettere valori ripetuti).
    #     Si esplora SOLO a partire dal nodo scelto dall'utente (non da
    #     tutti i nodi del grafo, a differenza del 6.4): la lunghezza qui
    #     è in NUMERO DI ARCHI, quindi va sottratto 1 al numero di nodi nel
    #     cammino quando la si stampa.
    # --------------------------------------------------------------------
    def get_cammino_vincolo_nodo(self, nodo_iniziale):
        self._best_cammino = []
        cammino = [nodo_iniziale]
        self._ricorsione_cammino_nodo(cammino)
        fatturato_totale = sum(nodo.Fatturato for nodo in self._best_cammino)
        return self._best_cammino, fatturato_totale

    def _ricorsione_cammino_nodo(self, cammino):
        if len(cammino) > len(self._best_cammino):
            self._best_cammino = copy.deepcopy(cammino)

        ultimo = cammino[-1]
        # in un grafo ORIENTATO uso .successors(), in uno NON orientato
        # uso .neighbors(): sono i soli punti da cambiare per adattare
        # questo pattern da un caso all'altro
        for successore in self._graph.successors(ultimo):
            if successore not in cammino and successore.Fatturato <= ultimo.Fatturato:
                cammino.append(successore)
                self._ricorsione_cammino_nodo(cammino)
                cammino.pop()

    # --------------------------------------------------------------------
    # 6.4 CAMMINO SEMPLICE DI LUNGHEZZA MASSIMA, PROVANDO OGNI NODO DEL
    #     GRAFO COME PARTENZA (quando l'utente non sceglie un nodo di
    #     partenza, o il testo chiede "il" cammino più lungo in assoluto),
    #     CON VINCOLO SUL PESO DELL'ARCO STRETTAMENTE CRESCENTE lungo il
    #     cammino. Pattern visto nella simulazione d'esame: si tiene traccia
    #     dell'ultimo peso percorso (lastWeight) e lo si passa alla
    #     chiamata ricorsiva successiva.
    # --------------------------------------------------------------------
    def get_cammino_peso_crescente(self):
        self._best_cammino = []

        for nodo_iniziale in self._graph.nodes:
            # provo subito tutti gli archi uscenti dal nodo di partenza,
            # per avere un "ultimo peso" di riferimento al primo passo
            for _, vicino, dati in self._graph.out_edges(nodo_iniziale, data=True):
                cammino = [nodo_iniziale, vicino]
                self._ricorsione_peso_crescente(cammino, dati["weight"])

        return self._best_cammino

    def _ricorsione_peso_crescente(self, cammino, ultimo_peso):
        if len(cammino) > len(self._best_cammino):
            self._best_cammino = copy.deepcopy(cammino)

        corrente = cammino[-1]
        for _, successore, dati in self._graph.out_edges(corrente, data=True):
            peso = dati["weight"]
            if peso > ultimo_peso and successore not in cammino:  # STRETTAMENTE crescente
                cammino.append(successore)
                self._ricorsione_peso_crescente(cammino, peso)
                cammino.pop()

    # Variante NON orientata, peso dell'arco strettamente CRESCENTE lungo
    # il cammino, con il nodo di partenza dato (pattern "classico" visto
    # anche nel codice di esempio generico del corso):
    def get_cammino_peso_crescente_da_nodo(self, nodo_iniziale):
        self._best_cammino = []
        cammino = [nodo_iniziale]
        self._ricorsione_peso_crescente_non_orientato(cammino)
        return self._best_cammino

    def _ricorsione_peso_crescente_non_orientato(self, cammino):
        if len(cammino) > len(self._best_cammino):
            self._best_cammino = copy.deepcopy(cammino)
        for vicino in self._graph.neighbors(cammino[-1]):
            if vicino not in cammino:
                # al primo passo (len(cammino) == 1) non c'è un arco
                # precedente con cui confrontare: si accetta sempre
                if len(cammino) == 1 or \
                   self._graph[cammino[-1]][vicino]["weight"] > self._graph[cammino[-2]][cammino[-1]]["weight"]:
                    cammino.append(vicino)
                    self._ricorsione_peso_crescente_non_orientato(cammino)
                    cammino.pop()

    # --------------------------------------------------------------------
    # 6.5 CAMMINO DI LUNGHEZZA ESATTA TRA DUE NODI DATI (partenza e
    #     arrivo), che massimizza il peso complessivo. La condizione di
    #     terminazione richiede DUE cose insieme: lunghezza raggiunta E
    #     trovarsi sul nodo di arrivo giusto.
    # --------------------------------------------------------------------
    def get_cammino_lunghezza_esatta(self, nodo_partenza, nodo_arrivo, lunghezza):
        self._best_cammino = []
        self._best_peso = 0
        cammino = [nodo_partenza]
        self._ricorsione_lunghezza_esatta(cammino, nodo_arrivo, lunghezza)
        return self._best_cammino, self._best_peso

    def _ricorsione_lunghezza_esatta(self, cammino, nodo_arrivo, lunghezza):
        if len(cammino) == lunghezza:
            if cammino[-1] == nodo_arrivo:
                peso = self._peso_cammino(cammino)
                if peso > self._best_peso:
                    self._best_peso = peso
                    self._best_cammino = copy.deepcopy(cammino)
            return  # lunghezza raggiunta (sul nodo giusto o no): non si prosegue oltre

        for vicino in self._graph.neighbors(cammino[-1]):
            if vicino not in cammino:
                cammino.append(vicino)
                self._ricorsione_lunghezza_esatta(cammino, nodo_arrivo, lunghezza)
                cammino.pop()

    def _peso_cammino(self, cammino):
        return sum(
            self._graph[cammino[i]][cammino[i + 1]]["weight"]
            for i in range(len(cammino) - 1)
        )

    # --------------------------------------------------------------------
    # 6.6 CAMMINO MASSIMO TRAMITE DFS TREE — scorciatoia veloce (NON un
    #     backtracking esaustivo!), utile come doppio controllo o se il
    #     testo lo consente esplicitamente. ATTENZIONE: su un grafo con
    #     cicli non garantisce di trovare il cammino semplice più lungo in
    #     assoluto, perché resta legato a UN SOLO albero di visita.
    # --------------------------------------------------------------------
    def get_cammino_massimo_via_dfs(self, nodo_partenza):
        cammino_migliore = []
        albero = nx.dfs_tree(self._graph, nodo_partenza)

        for nodo in albero.nodes():
            cammino = [nodo]
            while cammino[0] != nodo_partenza:
                predecessore = next(albero.predecessors(cammino[0]))
                cammino.insert(0, predecessore)
            if len(cammino) > len(cammino_migliore):
                cammino_migliore = cammino

        return cammino_migliore

# ==============================================================================
# 8. UI/view.py — ELEMENTI GRAFICI RICORRENTI (Flet)
# ==============================================================================
"""
# Dropdown "vuota", riempita a runtime dal controller (valori stringa):
self._ddCountry = ft.Dropdown(label="Paese")

# Dropdown riempita con OGGETTI (nodi del grafo), dopo la creazione del grafo:
self._ddCliente = ft.Dropdown(label="Cliente")

# TextField per un intero N:
self._txtInN = ft.TextField(label="Numero di elementi")

# Bottoni che chiamano handler del controller:
self._btnCreaGrafo = ft.ElevatedButton(text="Crea grafo", on_click=self._controller.handleCreaGrafo)
self._btnStampaInfo = ft.ElevatedButton(text="Stampa Info", on_click=self._controller.handleStampaInfo)

# ListView per l'output:
self._txt_result = ft.ListView(expand=1, spacing=10, padding=20, auto_scroll=True)
self._page.controls.append(self._txt_result)

# Alert di errore/validazione (metodo nella view, richiamato dal controller):
def create_alert(self, message):
    dlg = ft.AlertDialog(title=ft.Text(message))
    self._page.dialog = dlg
    dlg.open = True
    self._page.update()

def update_page(self):
    self._page.update()
"""

# ==============================================================================
# 9. main.py — BOILERPLATE D'AVVIO (di solito già pronto, invariato)
# ==============================================================================
"""
import flet as ft
from model.model import Model
from UI.view import View
from UI.controller import Controller

def main(page: ft.Page):
    my_model = Model()
    my_view = View(page)
    my_controller = Controller(my_view, my_model)
    my_view.set_controller(my_controller)
    my_view.load_interface()

ft.app(target=main)
"""

# ==============================================================================
# 10. TESTARE IL MODEL SENZA AVVIARE L'INTERFACCIA GRAFICA (testModel.py)
# ==============================================================================
# Stesso trucco già visto per IMDB_2: un piccolo script a parte (allo
# stesso livello di main.py), che chiama i metodi del Model direttamente
# con valori scelti a mano, per scoprire subito eventuali errori prima di
# passare a collegare controller e view.
"""
from model.model import Model

model = Model()
model.buildGraph('Rock')            # genere/paese scelto a mano, plausibile per il test

print(model.getNumNodi())
print(model.getNumEdges())
print(model.getBestArtist())        # o qualunque altro metodo da verificare
"""

# ==============================================================================
# 11. RICHIAMO RAPIDO NETWORKX (le funzioni usate più di frequente)
# ==============================================================================
"""
Grafo:
    graph = nx.Graph()      # non orientato
    graph = nx.DiGraph()    # orientato
    graph.clear()

Nodi / archi:
    graph.add_node(nodo) / graph.add_nodes_from(lista_nodi)
    graph.add_edge(n1, n2, weight=w) / graph.add_edges_from(lista_archi)
    graph.has_node(nodo) / graph.has_edge(n1, n2)
    len(graph.nodes) / graph.number_of_nodes()
    len(graph.edges) / graph.number_of_edges()

Non orientato:
    graph.neighbors(nodo)
    graph.degree(nodo) / graph.degree()          # iterabile di (nodo, grado)

Orientato:
    graph.predecessors(nodo) / graph.successors(nodo)
    graph.in_degree(nodo) / graph.out_degree(nodo)
    graph.in_edges(nodo, data=True) / graph.out_edges(nodo, data=True)
    # iterano su TERNE (sorgente, destinazione, dict_attributi): utile per
    # sommare i pesi degli archi entranti/uscenti di un nodo, vedi sez. 5.1

Componenti connesse (non orientato):
    nx.number_connected_components(graph)
    nx.connected_components(graph)               # generatore di insiemi di nodi
    nx.node_connected_component(graph, nodo)
    nx.is_connected(graph)

Componenti connesse (orientato):
    nx.strongly_connected_components(graph)      # rispetta il verso degli archi
    nx.weakly_connected_components(graph)        # ignora il verso degli archi
    nx.number_weakly_connected_components(graph)

Esplorazione e cammini minimi (se richiesti dal testo):
    nx.bfs_tree(graph, source) / nx.dfs_tree(graph, source)
    nx.shortest_path(graph, n1, n2)                          # non pesato
    nx.dijkstra_path(graph, n1, n2, weight='weight')          # pesi positivi
    nx.bellman_ford_path(graph, n1, n2, weight='weight')      # pesi anche negativi
"""
Grafo
graph = nx.Graph()  # grafo non orientato
graph = nx.DiGraph()  # grafo orientato
self._graph.clear()
Nodi
graph.nodes
graph.has_node(node)
graph.add_node(node)
graph.add_nodes_from(nodes)
Numero
di
nodi
nodes_number = len(self.graph.nodes)
nodes_number = nx.number_of_nodes(graph)
nodes_number = graph.number_of_nodes()
Archi
graph.edges
graph.has_edge(node1, node2)
graph.add_edge(node1, node2)
graph.add_edges_from(edges)
Numero
di
archi
edges_number = len(graph.edges)
edges_number = nx.number_of_edges(graph)
edges_number = graph.number_of_edges()
Grafo
non
orientato
graph.neighbors(node)
graph.degree(node)
Grafo
orientato
graph.predecessors(node)
graph.successors(node)
graph.in_degree(node)
graph.out_degree(node)
Componenti
connesse
grafo
non
orientato
nx.number_connected_components(graph)  # numero di componenti connesse
nx.connected_components(graph)  # componenti connesse del grafo
nx.node_connected_component(graph, node)  # componenti connesse del nodo del grafo
nx.is_connected(graph)
Componenti
connesse
grafo
orientato
nx.strongly_connected_components(graph)
nx.weakly_connected_components(graph)
Esplorazione
nx.bfs_tree(graph, source_node)
nx.dfs_tree(graph, source_node)
nx.bfs_edges(graph, source_node)  # lista degli archi nell'ordine in cui sono stati esplorati da BFS
nx.dfs_edges(graph, source_node)  # lista degli archi nell’ordine in cui sono statu esplorati da DFS
Cammino
minimo
grafo
non
pesato / cammino
minimo
nx.shortest_path(graph, node1, node2)
Cammino
minimo
grafo
pesato / cammino
di
costo
minimo
nx.shortest_path(graph, node1, node2, weight='peso')  # pesi positivi
nx.dijkstra_path(graph, node1, node2, weight='peso')  # pesi positivi
nx.bellman_ford_path(graph, node1, node2, weight='peso')  # pesi positivi e negativi

# ==============================================================================
# 12. itertools E collections — STRUMENTI PYTHON USATI SPESSO SU CHINOOK
# ==============================================================================
"""
from collections import defaultdict
from itertools import combinations

# defaultdict(int): come un dizionario normale, ma se si legge/accumula su
# una chiave non ancora presente, viene creata automaticamente con un
# valore di default (0 per int, [] per list, {} per dict...) invece di
# sollevare KeyError. Utilissimo per accumulare conteggi/somme per chiave:
popolarita = defaultdict(int)
for artist_id, num_brani in [(1, 3), (2, 5), (1, 2)]:
    popolarita[artist_id] += num_brani   # niente bisogno di controllare "if artist_id not in..."

# defaultdict(dict): dizionario di dizionari, comodo per raggruppare terne
# (a, b, valore) in {a: {b: valore}}, come nella sezione 4.4:
mappa = defaultdict(dict)
for cliente, artista, conteggio in [(1, 10, 2), (1, 11, 5), (2, 10, 1)]:
    mappa[cliente][artista] = conteggio

# itertools.combinations(iterabile, 2): genera tutte le coppie possibili
# (senza ripetizioni, senza badare all'ordine) degli elementi passati —
# equivalente, ma più leggibile, del doppio ciclo for i in range(len(lista))
# for j in range(i+1, len(lista)):
for a, b in combinations([10, 11, 12], 2):
    pass  # produce (10,11), (10,12), (11,12) — mai (11,10) né (10,10)
"""