-- =========================================================
-- Checkers DB schema (MySQL 8.0+)
-- Sin triggers, compatible con InnoDB
-- =========================================================

-- Opcional: crear BD y ajustar charset/collation
 CREATE DATABASE IF NOT EXISTS checkers
   DEFAULT CHARACTER SET utf8mb4
   DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE checkers;

DROP TABLE IF EXISTS `authtoken`;
DROP TABLE IF EXISTS `movesmatch`;
DROP TABLE IF EXISTS `matches`;
DROP TABLE IF EXISTS `users`;

SET foreign_key_checks = 1;

-- -----------------------------------
-- users
-- -----------------------------------
CREATE TABLE `users` (
  `userid`        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `email`         VARCHAR(255)    NOT NULL,
  `username`      VARCHAR(50)     NOT NULL,
  `name`          VARCHAR(100)    NULL,
  `surname`       VARCHAR(100)    NULL,
  `password_hash` VARCHAR(255)    NOT NULL,
  `birthdate`     DATE            NULL,
  `country`       VARCHAR(80)     NULL,
  `created_at`    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`userid`),
  UNIQUE KEY `ux_users_email` (`email`),
  UNIQUE KEY `ux_users_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- -----------------------------------
-- matches
-- -----------------------------------
-- status   : waiting | ongoing | finished | aborted
-- result   : white | black | draw | none
-- reason   : normal | resign | timeout | illegal | agreement | abandon | none
CREATE TABLE `matches` (
  `matchid`    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `startedat`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `finishedat` DATETIME        NULL,
  `whiteuser`  BIGINT UNSIGNED NULL,
  `blackuser`  BIGINT UNSIGNED NULL,
  `result`     ENUM('white','black','draw','none') NOT NULL DEFAULT 'none',
  `reason`     ENUM('normal','resign','timeout','agreement','abandon','none') NOT NULL DEFAULT 'none',
  `status`     ENUM('waiting','ongoing','finished','aborted') NOT NULL DEFAULT 'waiting',
  PRIMARY KEY (`matchid`),
  KEY `idx_matches_status` (`status`),
  KEY `idx_matches_players` (`whiteuser`,`blackuser`),
  CONSTRAINT `fk_matches_whiteuser`
    FOREIGN KEY (`whiteuser`) REFERENCES `users`(`userid`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_matches_blackuser`
    FOREIGN KEY (`blackuser`) REFERENCES `users`(`userid`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- -----------------------------------
-- match_moves
-- Una fila por movimiento que pertenece a una partida
-- Nota: Para MySQL < 8.0.13 elimina el DEFAULT y manéjalo desde la app.
-- -----------------------------------
CREATE TABLE `match_moves` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `matchid` BIGINT UNSIGNED NOT NULL,
  `move_number` INT UNSIGNED NOT NULL,
  `player` ENUM('white','black') NOT NULL,
  `move` JSON NOT NULL,
  `createdat` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `ux_match_move_number` (`matchid`, `move_number`),
  KEY `ix_match_createdat` (`matchid`, `createdat`),
  CONSTRAINT `fk_match_moves_match`
    FOREIGN KEY (`matchid`) REFERENCES `matches`(`matchid`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- -----------------------------------
-- authtoken (refresh tokens)
-- -----------------------------------
CREATE TABLE `authtoken` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `userid`        BIGINT UNSIGNED NOT NULL,
  `refreshtoken`  VARCHAR(255)    NOT NULL,
  `expiresat`     DATETIME        NOT NULL,
  `createdat`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ux_authtoken_token` (`refreshtoken`),
  KEY `idx_authtoken_user_expires` (`userid`,`expiresat`),
  CONSTRAINT `fk_authtoken_user`
    FOREIGN KEY (`userid`) REFERENCES `users`(`userid`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
