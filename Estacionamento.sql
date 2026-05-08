PRAGMA foreign_keys = ON;

-- Setores do estacionamento (A, B, C)
CREATE TABLE setor (
    id        TEXT PRIMARY KEY,
    descricao TEXT
);

-- Vagas de cada setor
CREATE TABLE vaga (
    spotId       TEXT PRIMARY KEY,
    sectorId     TEXT REFERENCES setor(id),
    currentState TEXT DEFAULT 'FREE',
    lastChangeTs TEXT,
    lastEventId  TEXT
);

-- Historico de eventos recebidos pelo sensor
CREATE TABLE vaga_evento (
    eventId         TEXT PRIMARY KEY,
    eventTs         TEXT,
    sectorId        TEXT REFERENCES setor(id),
    spotId          TEXT REFERENCES vaga(spotId),
    estado          TEXT,
    payloadCru_json TEXT
);

-- Resumo de ocupacao por setor (tirado de tempos em tempos)
CREATE TABLE atualizacao_setores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    atualizacaoTs       TEXT,
    sectorId            TEXT REFERENCES setor(id),
    quantidadeOcupadas  INTEGER,
    quantidadeLivres    INTEGER,
    porcentagemOcupacao REAL
);

-- Problemas detectados nas vagas
CREATE TABLE incidentes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    abriuTs       TEXT,
    fechouTs      TEXT,
    tipo          TEXT,
    gravidade     TEXT,
    sectorId      TEXT REFERENCES setor(id),
    vagaId        TEXT REFERENCES vaga(spotId),
    evidenciaJson TEXT,
    status        TEXT DEFAULT 'ABERTO'
);

-- Recomendacoes geradas quando um setor lota
CREATE TABLE log_recomendacoes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    logTs            TEXT,
    setorOriginario  TEXT REFERENCES setor(id),
    setorRecomendado TEXT REFERENCES setor(id),
    razao            TEXT,
    dadosJson        TEXT
);

-- Inserindo os 3 setores
INSERT INTO setor VALUES ('A', 'Setor A');
INSERT INTO setor VALUES ('B', 'Setor B');
INSERT INTO setor VALUES ('C', 'Setor C');

-- Inserindo as 90 vagas
INSERT INTO vaga (spotId, sectorId) VALUES
('A-01','A'),('A-02','A'),('A-03','A'),('A-04','A'),('A-05','A'),
('A-06','A'),('A-07','A'),('A-08','A'),('A-09','A'),('A-10','A'),
('A-11','A'),('A-12','A'),('A-13','A'),('A-14','A'),('A-15','A'),
('A-16','A'),('A-17','A'),('A-18','A'),('A-19','A'),('A-20','A'),
('A-21','A'),('A-22','A'),('A-23','A'),('A-24','A'),('A-25','A'),
('A-26','A'),('A-27','A'),('A-28','A'),('A-29','A'),('A-30','A'),
('B-01','B'),('B-02','B'),('B-03','B'),('B-04','B'),('B-05','B'),
('B-06','B'),('B-07','B'),('B-08','B'),('B-09','B'),('B-10','B'),
('B-11','B'),('B-12','B'),('B-13','B'),('B-14','B'),('B-15','B'),
('B-16','B'),('B-17','B'),('B-18','B'),('B-19','B'),('B-20','B'),
('B-21','B'),('B-22','B'),('B-23','B'),('B-24','B'),('B-25','B'),
('B-26','B'),('B-27','B'),('B-28','B'),('B-29','B'),('B-30','B'),
('C-01','C'),('C-02','C'),('C-03','C'),('C-04','C'),('C-05','C'),
('C-06','C'),('C-07','C'),('C-08','C'),('C-09','C'),('C-10','C'),
('C-11','C'),('C-12','C'),('C-13','C'),('C-14','C'),('C-15','C'),
('C-16','C'),('C-17','C'),('C-18','C'),('C-19','C'),('C-20','C'),
('C-21','C'),('C-22','C'),('C-23','C'),('C-24','C'),('C-25','C'),
('C-26','C'),('C-27','C'),('C-28','C'),('C-29','C'),('C-30','C');
