# ==============================================================================
# 4. model/model.py — COSTRUZIONE DEL GRAFO
# ==============================================================================
class Model_ESEMPIO:
    def __init__(self):
        # nx.Graph() per grafi non orientati, nx.DiGraph() per orientati
        self._graph = nx.Graph()
        self._nodi = []
        self._id_map = {}        # {id: oggetto}, utile quando gli archi arrivano come id "grezzi"
        self._best_lista = []
        self._best_punteggio = 0.0

    # --------------------------------------------------------------------
    # 4.1 GRAFO NON ORIENTATO, NON PESATO: arco tra due nodi se condividono
    #     almeno un elemento correlato (qui: due album con almeno un
    #     genere in comune tra le rispettive tracce). Pattern standard con
    #     doppio ciclo i<j (ogni coppia una volta sola, niente self-loop).
    # --------------------------------------------------------------------
    def costruisci_grafo_semplice(self):
        self._graph.clear()

        self._nodi = DAO.get_all_albums()
        for album in self._nodi:
            DAO.popola_tracce_album(album)

        self._graph.add_nodes_from(self._nodi)

        for i, a1 in enumerate(self._nodi):
            for a2 in self._nodi[i + 1:]:
                if self._condividono_genere(a1, a2):
                    self._graph.add_edge(a1, a2)  # nessun "weight": grafo non pesato

    def _condividono_genere(self, album1, album2):
        if not album1.Tracks or not album2.Tracks:
            return False
        generi1 = set(t.GenreId for t in album1.Tracks if t.GenreId is not None)
        generi2 = set(t.GenreId for t in album2.Tracks if t.GenreId is not None)
        return len(generi1 & generi2) > 0

    # --------------------------------------------------------------------
    # 4.2 GRAFO NON ORIENTATO PESATO: arco tra due nodi se condividono
    #     almeno un elemento in un insieme associato; peso = numero di
    #     elementi in comune (qui: playlist in comune tra due artisti).
    # --------------------------------------------------------------------
    def costruisci_grafo_pesato(self):
        self._graph.clear()

        self._nodi = DAO.get_all_artisti()
        self._graph.add_nodes_from(self._nodi)

        coppie_playlist = DAO.get_coppie_artista_playlist()
        for artista in self._nodi:
            artista.Playlists = set(coppie_playlist.get(artista.ArtistId, set()))

        for i in range(len(self._nodi)):
            for j in range(i + 1, len(self._nodi)):
                a1 = self._nodi[i]
                a2 = self._nodi[j]
                comuni = a1.Playlists & a2.Playlists
                if comuni:
                    self._graph.add_edge(a1, a2, weight=len(comuni))

    # --------------------------------------------------------------------
    # 4.3 GRAFO ORIENTATO E PESATO, con verso determinato dal confronto di
    #     un valore numerico (qui: fatturato) tra i due nodi, e peso =
    #     somma dei due valori. In caso di PARITA' si inseriscono DUE
    #     archi, uno per verso: pattern ricorrente in quasi tutti gli
    #     esami visti (sia su IMDB_2 sia su Chinook).
    # --------------------------------------------------------------------
    def costruisci_grafo_orientato(self, paese):
        self._graph.clear()

        self._nodi = DAO.get_clienti_per_paese(paese)
        self._id_map = {c.CustomerId: c for c in self._nodi}
        self._graph.add_nodes_from(self._nodi)

        coppie_cliente_artista = DAO.get_coppie_cliente_artista(paese)

        for i in range(len(self._nodi)):
            for j in range(i + 1, len(self._nodi)):
                c1 = self._nodi[i]
                c2 = self._nodi[j]

                artisti1 = set(coppie_cliente_artista.get(c1.CustomerId, []))
                artisti2 = set(coppie_cliente_artista.get(c2.CustomerId, []))

                if not (artisti1 & artisti2):
                    continue  # nessun artista in comune: nessun arco

                peso = c1.Fatturato + c2.Fatturato

                if c1.Fatturato > c2.Fatturato:
                    self._graph.add_edge(c1, c2, weight=peso)
                elif c2.Fatturato > c1.Fatturato:
                    self._graph.add_edge(c2, c1, weight=peso)
                else:
                    # parità: arco in ENTRAMBI i versi
                    self._graph.add_edge(c1, c2, weight=peso)
                    self._graph.add_edge(c2, c1, weight=peso)

    # --------------------------------------------------------------------
    # 4.4 GRAFO ORIENTATO E PESATO COSTRUITO "PER GRUPPI" ANZICHE' CON IL
    #     DOPPIO CICLO i<j: quando l'arco dipende da una TERZA entità che
    #     "mette in relazione" più nodi contemporaneamente (qui: un cliente
    #     che compra brani di più artisti nello stesso genere), conviene
    #     raggruppare prima i dati per quella terza entità con un
    #     defaultdict, e poi generare tutte le coppie all'interno di ogni
    #     gruppo con itertools.combinations — invece di confrontare ogni
    #     coppia di nodi con una query/ciclo separato per ciascuna. Il peso
    #     qui è la "popolarità" complessiva (somma di tutti i brani
    #     acquistati di quell'artista, su TUTTI i clienti), non il semplice
    #     conteggio della singola coppia.
    # --------------------------------------------------------------------
    def costruisci_grafo_per_gruppi(self, genere):
        self._graph.clear()

        self._nodi = DAO.get_all_artisti_per_genere(genere)
        self._id_map = {a.ArtistId: a for a in self._nodi}
        self._graph.add_nodes_from(self._nodi)

        terne = DAO.get_conteggi_cliente_artista(genere)  # (CustomerId, ArtistId, NumBrani)

        # raggruppo per cliente: {CustomerId: {ArtistId: NumBrani}}
        mappa_cliente = defaultdict(dict)
        for customer_id, artist_id, num_brani in terne:
            mappa_cliente[customer_id][artist_id] = num_brani

        # popolarità complessiva di ciascun artista (somma su tutti i clienti)
        popolarita = defaultdict(int)
        for artisti_del_cliente in mappa_cliente.values():
            for artist_id, num_brani in artisti_del_cliente.items():
                popolarita[artist_id] += num_brani

        # per ogni cliente, genero un arco per OGNI COPPIA di artisti che
        # ha acquistato: itertools.combinations(iterabile, 2) genera tutte
        # le coppie possibili (senza ripetizioni e senza ordine) degli
        # elementi passati, qui le chiavi (ArtistId) del dizionario interno
        for artisti_del_cliente in mappa_cliente.values():
            for id_a, id_b in itertools.combinations(artisti_del_cliente.keys(), 2):
                pop_a = popolarita[id_a]
                pop_b = popolarita[id_b]
                peso = pop_a + pop_b

                nodo_a = self._id_map[id_a]
                nodo_b = self._id_map[id_b]

                if pop_a > pop_b:
                    self._graph.add_edge(nodo_a, nodo_b, weight=peso)
                elif pop_b > pop_a:
                    self._graph.add_edge(nodo_b, nodo_a, weight=peso)
                else:
                    self._graph.add_edge(nodo_a, nodo_b, weight=peso)
                    self._graph.add_edge(nodo_b, nodo_a, weight=peso)

    # --------------------------------------------------------------------
    # 5.1 NODO PIU' "INFLUENTE" IN UN GRAFO ORIENTATO: influenza definita
    #     come somma dei pesi degli archi USCENTI meno somma dei pesi
    #     degli archi ENTRANTI. Pattern molto ricorrente (compare uguale,
    #     a parte il nome, sia su Chinook sia nel codice di esempio
    #     generico del corso).
    # --------------------------------------------------------------------
    def get_nodo_piu_influente(self):
        if len(self._graph.nodes) == 0:
            return None, 0

        max_influenza = float('-inf')
        migliore = None

        for nodo in self._graph.nodes:
            peso_uscente = sum(
                self._graph[nodo][succ]["weight"]
                for succ in self._graph.successors(nodo)
            )
            peso_entrante = sum(
                self._graph[pred][nodo]["weight"]
                for pred in self._graph.predecessors(nodo)
            )
            influenza = peso_uscente - peso_entrante

            if influenza > max_influenza:
                max_influenza = influenza
                migliore = nodo

        return migliore, max_influenza

    # --------------------------------------------------------------------
    # 5.2 NODO DI GRADO MASSIMO / MASSIMA SOMMA DEI PESI DEGLI ARCHI
    #     INCIDENTI — grafo NON orientato (vedi anche il vademecum IMDB_2
    #     per la versione già commentata in dettaglio)
    # --------------------------------------------------------------------
    def get_nodo_grado_massimo(self):
        if len(self._graph.nodes) == 0:
            return None, 0
        max_grado = -1
        migliore = None
        for nodo, grado in self._graph.degree():
            if grado > max_grado:
                max_grado = grado
                migliore = nodo
        return migliore, max_grado

    def get_nodo_somma_pesi_massima(self):
        if len(self._graph.nodes) == 0:
            return None, 0
        max_somma = -1
        migliore = None
        for nodo in self._graph.nodes:
            somma = sum(
                self._graph[nodo][vicino]["weight"]
                for vicino in self._graph.neighbors(nodo)
            )
            if somma > max_somma:
                max_somma = somma
                migliore = nodo
        return migliore, max_somma

    # --------------------------------------------------------------------
    # 5.3 TOP-N ARCHI PER PESO DECRESCENTE (con e senza tie-break)
    # --------------------------------------------------------------------
    def get_top_n_archi(self, n=5):
        """Versione semplice, senza criterio esplicito in caso di parità
        (va bene quando il testo non lo richiede)."""
        if len(self._graph.edges) == 0:
            return []
        archi_pesati = [(u, v, self._graph[u][v]["weight"]) for u, v in self._graph.edges]
        return sorted(archi_pesati, key=lambda x: x[2], reverse=True)[:n]

    def get_top_n_archi_con_tiebreak(self, n=5):
        """Variante con tie-break multiplo: peso decrescente, poi nome del
        primo nodo, poi nome del secondo, entrambi crescenti (vedi anche
        vademecum IMDB_2 per la spiegazione della tupla chiave -x[2],...)."""
        if len(self._graph.edges) == 0:
            return []
        archi_pesati = [(u, v, self._graph[u][v]["weight"]) for u, v in self._graph.edges]
        archi_ordinati = sorted(
            archi_pesati,
            key=lambda x: (-x[2], x[0].Name, x[1].Name)
        )
        return archi_ordinati[:n]

    # --------------------------------------------------------------------
    # 5.4 COMPONENTI CONNESSE — GRAFO NON ORIENTATO
    # --------------------------------------------------------------------
    def get_numero_componenti_connesse(self):
        return nx.number_connected_components(self._graph)

    def get_componente_connessa_piu_grande(self):
        if len(self._graph.nodes) == 0:
            return []
        componenti = list(nx.connected_components(self._graph))
        return list(max(componenti, key=len))

    def get_componente_del_nodo(self, nodo):
        componenti = list(nx.connected_components(self._graph))
        for componente in componenti:
            if nodo in componente:
                return componente
        return None

    def get_dettagli_componente_ordinati_per_titolo(self, componente):
        """Esempio: per ciascun album della componente, (titolo, numero di
        tracce), ordinati alfabeticamente per titolo — schema di stampa
        molto comune per il punto 1.d di questi esami."""
        risultato = [(album.Title, album.get_numero_tracce()) for album in componente]
        risultato.sort(key=lambda x: x[0])
        return risultato

#============================================================================================
# MODEL esempio aggiuntivo
#============================================================================================
import copy
import networkx as nx
from database.DAO import DAO
class Model:
    def __init__(self):
        self._graph = nx.Graph()
        self._best_ = []
        self._best_ = 0

    def build_graph(self, ):
        self._graph.clear()
        nodes = DAO.get_nodes()
        self._graph.add_nodes_from(nodes)
        id_map_nodes = {}
        for node in nodes:
            id_map_nodes[node.] = node
        edges = DAO.get_edges(id_map_nodes)
        for edge in edges:
            if edge. in self._graph and edge. in self._graph:
                self._graph.add_edge(edge., edge., weight=edge.)
        return len(self._graph.nodes), len(self._graph.edges)

    def get_graph_details(self):
        # nodo di differenza di peso tra gli archi uscenti e gli archi entranti maggiore
        best_node = None
        best_weight = None
        nodes = self._graph.nodes
        for node in nodes:
            out_edges = self._graph.out_edges(node, data=True)
            out_weight = 0
            for edge in out_edges:
                out_weight += edge[2]["weight"]
            in_edges = self._graph.in_edges(node, data=True)
            in_weight = 0
            for edge in in_edges:
                in_weight += edge[2]["weight"]
            weight = out_weight - in_weight
            if best_weight is None or weight > best_weight:
                best_node = node
                best_weight = weight
        # nodi in ordine decrescente di differenza di peso tra gli archi uscenti e gli archi entranti
        best_nodes = []
        nodes = self._graph.nodes
        for node in nodes:
            out_edges = self._graph.out_edges(node, data=True)
            out_weight = 0
            for edge in out_edges:
                out_weight += edge[2]["weight"]
            in_edges = self._graph.in_edges(node, data=True)
            in_weight = 0
            for edge in in_edges:
                in_weight += edge[2]["weight"]
            weight = out_weight - in_weight
            best_nodes.append((node, weight))
        best_nodes = best_nodes.sort(key=lambda node: node[1], reverse=True)
        # nodi successori di un determinato nodo in ordine decrescente di differenza di peso tra gli archi uscenti e gli archi entranti
        best_nodes = []
        nodes = self._graph.successors(node)
        for node in nodes:
            out_edges = self._graph.out_edges(node, data=True)
            out_weight = 0
            for edge in out_edges:
                out_weight += edge[2]["weight"]
            in_edges = self._graph.in_edges(node, data=True)
            in_weight = 0
            for edge in in_edges:
                in_weight += edge[2]["weight"]
            weight = out_weight - in_weight
            best_nodes.append((node, weight))
        best_nodes = best_nodes.sort(key=lambda node: node[1], reverse=True)
        # archi in ordine di peso decrescente
        best_edges = sorted(self._graph.edges(data=True), key=lambda edge: edge[2]["weight"], reverse=True)
        # archi di peso massimo
        edges = sorted(self._graph.edges(data=True), key=lambda edge: edge[2]["weight"], reverse=True)
        if len(edges) == 0:
            best_edges = []
        best_edges = [edges[0]]
        for edge in edges[1:]:
            if edge[2]["weight"] == edges[0][2]["weight"]:
                best_edges.append(edge)
        # numero di componenti connesse
        connected_components_number = nx.number_connected_components(self._graph)
        # componenti connesse
        connected_components = list(nx.connected_components(self._graph))
        # componente connessa del nodo
        connected_component = list(nx.node_connected_component(self._graph, node))
        # componente connessa di lunghezza maggiore
        connected_components = list(nx.connected_components(self._graph))
        best_connected_component = []
        for connected_component in connected_components:
            if len(connected_component) > len(best_connected_component):
                best_connected_component = connected_component
        # componente connessa di lunghezza maggiore con i nodi in ordine di grado decrescente
        connected_components = list(nx.connected_components(self._graph))
        best_connected_component = []
        for connected_component in connected_components:
            if len(connected_component) > len(best_connected_component):
                nodes = []
                for node in connected_component:
                    nodes.append((node, self._graph.degree(node)))
                best_connected_component = sorted(nodes, key=lambda node: node[1], reverse=True)
        # componente connessa di lunghezza maggiore con i nodi in ordine di peso massimo decrescente
        connected_components = list(nx.connected_components(self._graph))
        best_connected_component = []
        for connected_component in connected_components:
            if len(connected_component) > len(best_connected_component):
                best_connected_component = connected_component
                nodes = []
                for node in connected_component:
                    nodes.append((node, self._get_max_weight(node)))
                best_connected_component = sorted(nodes, key=lambda node: node[1], reverse=True)
        return
        def _get_max_weight(self, node1):
            return max(self._graph.get_edge_data(node1, node2)['weight'] for node2 in self._graph.neighbors(node1))

    def get_(self, ):
        self._best_ = []
        self._best_ = 0
        self._recursion(partial, condition, 0)
        return

    def _recursion(partial, condition, (level)):
        if:  # condizione di terminazione
            return
        if condition:  # condizione di ottimalità
            self._best_ = copy.deepcopy(partial)
            self._best_ =
        for in:
            if not in:
                partial.append()
                self._recursion(partial, condition, (level+1))
                partial.pop()

    # cammino massimo
    def get_path(self):
        self._best_path = []
        path = []
        nodes = self._graph.nodes
        for node in nodes:
            path = [node]
            self._recursion(path)
        return self._best_path

    # cammino massimo con archi in ordine di attributo strettamente decrescente
    def _recursion(self, path):
        if len(path) > len(self._best_path):
            self._best_path = list(path)
        nodes = self._graph.neighbors(path[-1])
        for node in nodes:
            if node not in path:
                if node. < path[-1].:
                    path.append(node)
                    self._recursion(path)
                    path.pop()

    # cammino massimo dato il nodo di partenza
    def get_path(self, node):
        self._best_path = []
        path = [node]
        self._recursion(path)
        return self._best_path

    # cammino massimo
    def _recursion(self, path):
        if len(path) > len(self._best_path):
            self._best_path = copy.deepcopy(path)
        nodes = self._graph.neighbors(path[-1])
        for node in nodes:
            if node not in path:
                path.append(node)
                self._recursion(path)
                path.pop()

    # cammino massimo con archi in ordine di peso strettamente crescente
    def _recursion(self, path):
        if len(path) > len(self._best_path):
            self._best_path = copy.deepcopy(path)
        nodes = self._graph.neighbors(path[-1])
        for node in nodes:
            if node not in path:
                if len(path) == 1 or self._graph[path[-1]][node]["weight"] > self._graph[path[-2]][path[-1]]["weight"]:
                    path.append(node)
                    self._recursion(path)
                    path.pop()

    # cammino di costo massimo dati il nodo di partenza, il nodo di arrivo e la lunghezza
    def get_path(self, start_node, end_node, length):
        self._best_path = []
        self._best_weight = 0
        path = [start_node]
        self._recursion(path, end_node, length)
        return self._best_path, self._best_weight

    # cammino di costo massimo
    def _recursion(self, path, end_node, length):
        if len(path) == length:
            if path[-1] == end_node:
                if self.get_weight(path) > self._best_weight:
                    self._best_path = copy.deepcopy(path)
                    self._best_weight = self.get_weight(path)
            return
        nodes = self._graph.neighbors(path[-1])
        for node in nodes:
            if node not in path:
                path.append(node)
                self._recursion(path, end_node, length)
                path.pop()

    def get_weight(self, path):
        weight = 0
        for i in range( 0, len(path)-1):
            weight += self._graph[path[i]][path[i+1]]["weight"]
        return weight

    # cammino dati il nodo di partenza, il nodo di arrivo e il peso massimo
    def get_path(self, start_node, end_node, max_weight):
        self._best_path = []
        self._best_score = 0
        path = [start_node]
        self._recursion(path, start_node, end_node, max_weight)
        return self._best_path

    def _recursion(self, path, start_node, end_node, max_weight):
        if path[-1] == end_node:
            if self.get_score(start_node, path) > len(self._best_score):
                self._best_path = copy.deepcopy(path)
                self._best_score = self.get_score(path)
            return
        nodes = self._graph.neighbors(path[-1])
        for node in nodes:
            if node not in path:
                if self._graph[path[-1]][node]["weight"] >= max_weight:
                    path.append(node)
                    self._recursion(path, start_node, end_node, max_weight)
                    path.pop()

    def get_weight(self, node):
        out_edges = self._graph.out_edges(node, data=True)
        out_weight = 0
        for edge in out_edges:
            out_weight += edge[2]["weight"]
        in_edges = self._graph.in_edges(node, data=True)
        in_weight = 0
        for edge in in_edges:
            in_weight += edge[2]["weight"]
        weight = out_weight - in_weight
        return weight

    def get_score(self, start_node, path):
        score = 0
        for node in path[1:-1]:
            if self.get_weight(node) > self.get_weight(start_node):
                score += 1
        return score

    # cammino di costo massimo dato il nodo di partenza
    def get_path(self, node):
        self._best_path = []
        self._best_weight = 0
        path = [start]
        self._recursion(path)
        return self._best_path, self._best_weight

    # cammino di costo massimo con archi in ordine di peso strettamente decrescente
    def _recursion(self, path):
        if self.get_weight(path) > self._best_weight:
            self._best_path = copy.deepcopy(path)
            self._best_weight = self.get_weight(path)
        nodes = self._graph.neighbors(path[-1])
        for node in nodes:
            if node not in path:
                if len(path) == 1 or self._graph[path[-1]][node]["weight"] < self._graph[node[-2]][node[-1]]["weight"]:
                    path.append(node)
                    self._recursion(path)
                    path.pop()

    def get_weight(self, path):
        weight = 0
        for i in range( 0, len(path)-1):
            weight += self._graph[path[i]][path[i+1]]["weight"]
        return weight

    # lista di oggetti dato il numero di oggetti
    def get_list(self, number):
        self._best_list = []
        self._best_score = 0
        connected_components = _list(nx.connected_components(self._graph))
        if len(connected_components) < number:
            return None, 0
        _list = []
        self._recursion(connected_components, number, _list, 0)
        return self._best_list, self._best_score

    # lista di oggetti, in cui ogni oggetto appartiene a una componente connessa distinta
    def _recursion(self, connected_components, number, _list, index):
        if len(_list) == number:
            if self.get_score(path) < self._best_score:
                self._best_list = copy.deepcopy(_list)
                self._best_score = self.get_score(path)
            return
        if index >= len(connected_components) or (len(connected_components)-index) < (number-len(_list)):
            return
        connected_component = connected_components[index]
        for node in connected_component:
            _list.append(node)
            self._recursion(connected_components, number, _list, index+1)
            _list.pop()
        self._recursion(connected_components, number, _list, index+1)

    # lista di oggetti dato l'oggetto di partenza
    def get_list(self, node, max_score):
        self._best_list = []
        nodes = sorted(nx.node_connected_component(self._graph, node) - {node}, key=lambda node: node.id)
        _list = []
        if node.score > max_score:
            return [node]
        max_score = max_score - node.score
        self._recursion(_list, nodes, 0, max_score)
        self._best_list.append(node)
        return self._best_list

    # lista di oggetti di lunghezza massima, in cui ogni oggetto appartiene alla componente connessa dell'oggetto di partenza
    def _recursion(self, _list, nodes, score, max_score):
        if len(_list) > len(self._best_list):
            self._best_list = copy.deepcopy(_list)
        for node in nodes:
            if node not in _list or node.id > _list[-1].id:
                if score + node.score <= max_score:
                    _list.append(node)
                    self._recursion(_list, nodes, score+node.score, max_score)
                    _list.pop()

    # cammino massimo
    def get_longest_path(self, start_node):
        longest_path = []
        tree = nx.dfs_tree(self._graph, start_node)
        nodes = list(tree.nodes())
        for node in nodes:
            path = [node]
            while path[0] != start_node:
                predecessor = nx.predecessor(tree, start_node, path[0])
                path.insert(0, predecessor[0])
            if len(path) > len(longest_path):
                longest_path = copy.deepcopy(path)
        return longest_path