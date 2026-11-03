# DAO
from database.DB_connect import DBConnect
class DAO():
    def __init__(self):
        pass

    @staticmethod
    def get_():
        connection = DBConnect.get_connection()
        _list = []
        cursor = connection.cursor()
        query = """SELECT
                   FROM  """
        cursor.execute(query)
        for in cursor:
            _list.append()
        cursor.close()
        connection.close()
        return _list

    @staticmethod
    def get_nodes():
        connection = DBConnect.get_connection()
        nodes_list = []
        cursor = connection.cursor(dictionary=True)
        query = """SELECT
                   FROM  """
        cursor.execute(query)
        for node in cursor:
            nodes_list.append(Node(node[""]))
        cursor.close()
        connection.close()
        return nodes_list

    @staticmethod
    def get_edges(id_map_nodes):
        connection = DBConnect.get_connection()
        edges_list = []
        cursor = connection.cursor(dictionary=True)
        query = """SELECT
                   FROM  """
        cursor.execute(query)
        for edge in cursor:
            if edge["1"] in id_map_nodes and edge["2"] in id_map_nodes:
                edges_list.append(Edge(id_map_nodes[edge["1"]], id_map_nodes[edge["2"]], edge[""]))
        cursor.close()
        connection.close()
        return edges_list

# ==============================================================================
# DAO.py — PATTERN DI QUERY
# ==============================================================================
class DAO_ESEMPI:
    """raccoglie diversi metodi statici, ciascuno indipendente dagli altri, 
    da copiare uno alla volta nel proprio DAO reale a seconda di cosa serve."""
    # --------------------------------------------------------------------
    # 2.1 SELECT SEMPLICE -> lista di valori "leggeri" (per una dropdown)
    # --------------------------------------------------------------------
    @staticmethod
    def get_all_paesi():
        """Esempio: valori distinti di una colonna, per popolare una dropdown
        (qui i paesi dei clienti)."""
        conn = DBConnect.get_connection()
        risultati = []

        cursor = conn.cursor(dictionary=True)
        query = """
                SELECT DISTINCT c.Country
                FROM Customer c
                WHERE c.Country IS NOT NULL
                ORDER BY c.Country
                """
        cursor.execute(query)
        for row in cursor:
            risultati.append(row["Country"])

        cursor.close()
        conn.close()
        return risultati

    # --------------------------------------------------------------------
    # 2.2 SELECT CON AGGREGAZIONE (SUM/COUNT + GROUP BY) PER COSTRUIRE
    #     DIRETTAMENTE GLI OGGETTI NODO CON UN ATTRIBUTO CALCOLATO
    #     (qui: il fatturato totale di ciascun cliente, somma di
    #     Invoice.Total). Nota come l'alias "Fatturato" nella SELECT
    #     combaci con il nome del campo aggiuntivo nella dataclass
    #     Customer, cosi' da poter fare Customer(**row) subito dopo.
    # --------------------------------------------------------------------
    @staticmethod
    def get_clienti_per_paese(paese):
        conn = DBConnect.get_connection()
        risultati = []

        cursor = conn.cursor(dictionary=True)
        query = """
                SELECT c.*, SUM(i.Total) AS Fatturato
                FROM Customer c, Invoice i
                WHERE c.CustomerId = i.CustomerId
                AND c.Country = %s
                GROUP BY c.CustomerId
                ORDER BY c.CustomerId
                """
        # NB: "c.*" prende TUTTE le colonne di Customer così come sono
        # chiamate nel database (CamelCase): la dataclass Cliente_ESEMPIO
        # più sotto deve quindi avere i campi con ESATTAMENTE questi nomi
        # (CustomerId, FirstName, LastName, ...) per poter usare
        # Customer(**row); GROUP BY c.CustomerId è necessario perché c'è
        # una funzione di aggregazione (SUM) nella SELECT.
        cursor.execute(query, (paese,))
        for row in cursor:
            risultati.append(Cliente_ESEMPIO(**row))

        cursor.close()
        conn.close()
        return risultati

    # --------------------------------------------------------------------
    # 2.3 QUERY CHE RESTITUISCE COPPIE/DIZIONARI "GREZZI" DA USARE PER
    #     COSTRUIRE GLI ARCHI NEL MODEL (invece di popolare ogni nodo uno
    #     per uno): utile quando il criterio per l'arco coinvolge una
    #     TERZA entità (qui: quali artisti sono stati acquistati da quale
    #     cliente), attraversando una catena lunga di tabelle.
    #     Pattern: si restituisce un dict {id_nodo: [id_correlati]}, che
    #     il model trasformerà in insiemi per calcolare intersezioni.
    # --------------------------------------------------------------------
    @staticmethod
    def get_coppie_cliente_artista(paese):
        """Per ogni cliente del paese scelto, quali artisti ha acquistato
        (attraversando Customer -> Invoice -> InvoiceLine -> Track -> Album
        -> Artist). Restituisce un dizionario {CustomerId: [ArtistId, ...]},
        comodo da trasformare in insiemi nel model per calcolare
        intersezioni tra clienti."""
        conn = DBConnect.get_connection()
        risultati = {}

        cursor = conn.cursor(dictionary=True)
        query = """
                SELECT DISTINCT c.CustomerId, art.ArtistId
                FROM Customer c, Invoice i, InvoiceLine il, Track t, Album al, Artist art
                WHERE c.CustomerId = i.CustomerId
                AND i.InvoiceId = il.InvoiceId
                AND il.TrackId = t.TrackId
                AND t.AlbumId = al.AlbumId
                AND al.ArtistId = art.ArtistId
                AND c.Country = %s
                """
        cursor.execute(query, (paese,))
        for row in cursor:
            customer_id = row["CustomerId"]
            artist_id = row["ArtistId"]
            if customer_id not in risultati:
                risultati[customer_id] = []
            risultati[customer_id].append(artist_id)

        cursor.close()
        conn.close()
        return risultati

    # --------------------------------------------------------------------
    # 2.4 POPOLARE UN NODO GIA' CREATO CON UNA LISTA DI DETTAGLIO
    #     (qui: dato un album, la lista dei suoi brani/Track). Pattern
    #     identico a quello già visto per IMDB_2: una query "di dettaglio"
    #     per singolo nodo, invocata in un ciclo dal model dopo aver
    #     recuperato la lista dei nodi principali.
    # --------------------------------------------------------------------
    @staticmethod
    def popola_tracce_album(album):
        """Riceve un oggetto Album già creato e lo popola con la lista
        completa dei suoi Track (oggetti Track veri e propri, utile quando
        servono i dettagli di ciascun brano, es. il genere)."""
        conn = DBConnect.get_connection()
        risultati = []

        cursor = conn.cursor(dictionary=True)
        query = """
                SELECT t.*
                FROM Track t
                WHERE t.AlbumId = %s
                ORDER BY t.Name
                """
        cursor.execute(query, (album.AlbumId,))
        for row in cursor:
            risultati.append(Track_ESEMPIO(**row))
        album.Tracks = risultati

        cursor.close()
        conn.close()

    # --------------------------------------------------------------------
    # 2.5 SOLO GLI ID DI DETTAGLIO (quando non servono i dettagli
    #     dell'entità correlata, solo "quanti sono" o per confrontarli con
    #     un altro insieme di id): più leggero della 2.4.
    # --------------------------------------------------------------------
    @staticmethod
    def get_id_tracce_per_artista(artist_id):
        conn = DBConnect.get_connection()
        risultati = []

        cursor = conn.cursor(dictionary=True)
        query = """
                SELECT t.TrackId
                FROM Track t, Album al
                WHERE t.AlbumId = al.AlbumId
                AND al.ArtistId = %s
                """
        cursor.execute(query, (artist_id,))
        for row in cursor:
            risultati.append(row["TrackId"])

        cursor.close()
        conn.close()
        return risultati

    # --------------------------------------------------------------------
    # 2.6 COPPIE (id_principale, id_correlato) ATTRAVERSO UNA TABELLA
    #     PONTE A TRE LIVELLI (qui: Artist -> Album -> Track ->
    #     PlaylistTrack -> Playlist): stesso pattern della 2.3, ma con una
    #     catena di JOIN più lunga, tipico quando l'entità ponte finale
    #     (Playlist) è distante diversi passaggi dal nodo del grafo
    #     (Artist).
    # --------------------------------------------------------------------
    @staticmethod
    def get_coppie_artista_playlist():
        conn = DBConnect.get_connection()
        risultati = {}

        cursor = conn.cursor(dictionary=True)
        query = """
                SELECT DISTINCT art.ArtistId, pt.PlaylistId
                FROM Artist art, Album al, Track t, PlaylistTrack pt
                WHERE art.ArtistId = al.ArtistId
                AND al.AlbumId = t.AlbumId
                AND t.TrackId = pt.TrackId
                """
        cursor.execute(query)
        for row in cursor:
            artist_id = row["ArtistId"]
            playlist_id = row["PlaylistId"]
            if artist_id not in risultati:
                risultati[artist_id] = []
            risultati[artist_id].append(playlist_id)

        cursor.close()
        conn.close()
        return risultati

    # --------------------------------------------------------------------
    # 2.7 CONTEGGIO/AGGREGAZIONE SEMPLICE PER UN SINGOLO NODO (query "al
    #     volo", chiamata ad esempio solo al momento della stampa finale,
    #     non durante la costruzione del grafo): usa cursor.fetchone()
    #     invece di iterare sul cursore, dato che la query restituisce
    #     sempre UNA SOLA riga (un aggregato).
    # --------------------------------------------------------------------
    @staticmethod
    def get_numero_album_per_artista(artist_id):
        conn = DBConnect.get_connection()

        cursor = conn.cursor(dictionary=True)
        query = """
                SELECT COUNT(DISTINCT al.AlbumId) AS NumAlbum
                FROM Album al
                WHERE al.ArtistId = %s
                """
        cursor.execute(query, (artist_id,))
        row = cursor.fetchone()

        cursor.close()
        conn.close()
        return row["NumAlbum"] if row else 0

    # --------------------------------------------------------------------
    # 2.8 QUERY CHE RESTITUISCE TERNE (id1, id2, valore) GIA' PRONTE PER
    #     UN CONTEGGIO "PER COPPIA" (qui: quanti brani di un dato genere
    #     ha comprato ciascun cliente, per ciascun artista): utile quando
    #     il peso dell'arco dipende da un conteggio raggruppato su due
    #     dimensioni insieme (cliente, artista). Il model poi raggruppa
    #     questi risultati per cliente con un defaultdict (sezione 4.3) e
    #     usa itertools.combinations per generare le coppie di archi.
    # --------------------------------------------------------------------
    @staticmethod
    def get_conteggi_cliente_artista(genere):
        conn = DBConnect.get_connection()
        risultati = []

        cursor = conn.cursor(dictionary=True)
        query = """
                SELECT i.CustomerId, art.ArtistId, COUNT(*) AS NumBrani
                FROM Invoice i, InvoiceLine il, Track t, Genre g, Artist art, Album al
                WHERE i.InvoiceId = il.InvoiceId
                AND t.TrackId = il.TrackId
                AND t.AlbumId = al.AlbumId
                AND g.GenreId = t.GenreId
                AND art.ArtistId = al.ArtistId
                AND g.Name = %s
                GROUP BY i.CustomerId, art.ArtistId
                """
        cursor.execute(query, (genere,))
        for row in cursor:
            risultati.append((row["CustomerId"], row["ArtistId"], row["NumBrani"]))

        cursor.close()
        conn.close()
        return risultati