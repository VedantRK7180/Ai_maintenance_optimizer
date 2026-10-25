-- AI Maintenance Optimizer: schema-only export
-- Safe for review: contains no INSERT statements, technician names, or DROP TABLE commands.
-- Import into an empty database. Create the database separately if needed.
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE `machine_type` (
  `machine_type_id` int NOT NULL AUTO_INCREMENT,
  `type_name` varchar(100) NOT NULL,
  `model_key` varchar(50) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`machine_type_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `machine` (
  `machine_id` int NOT NULL AUTO_INCREMENT,
  `machine_name` varchar(50) NOT NULL,
  `operating_hours` decimal(10,2) DEFAULT '0.00',
  `criticality` varchar(20) NOT NULL,
  `production_importance` varchar(20) NOT NULL,
  `status` varchar(30) NOT NULL,
  `machine_type_id` int NOT NULL,
  PRIMARY KEY (`machine_id`),
  UNIQUE KEY `machine_name` (`machine_name`),
  KEY `machine_type_id` (`machine_type_id`),
  CONSTRAINT `machine_ibfk_1` FOREIGN KEY (`machine_type_id`) REFERENCES `machine_type` (`machine_type_id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `technician` (
  `technician_id` int NOT NULL AUTO_INCREMENT,
  `technician_name` varchar(100) NOT NULL,
  `specialization` varchar(100) NOT NULL,
  `availability_status` varchar(20) NOT NULL,
  PRIMARY KEY (`technician_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `spare_part` (
  `spare_part_id` int NOT NULL AUTO_INCREMENT,
  `part_name` varchar(100) NOT NULL,
  `machine_type_id` int NOT NULL,
  `quantity_available` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`spare_part_id`),
  KEY `machine_type_id` (`machine_type_id`),
  CONSTRAINT `spare_part_ibfk_1` FOREIGN KEY (`machine_type_id`) REFERENCES `machine_type` (`machine_type_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `maintenance` (
  `maintenance_id` int NOT NULL AUTO_INCREMENT,
  `machine_id` int NOT NULL,
  `technician_id` int DEFAULT NULL,
  `maintenance_type` varchar(100) NOT NULL,
  `scheduled_date` date DEFAULT NULL,
  `start_time` time DEFAULT NULL,
  `end_time` time DEFAULT NULL,
  `status` varchar(30) NOT NULL,
  `priority` varchar(20) NOT NULL,
  `notes` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`maintenance_id`),
  KEY `machine_id` (`machine_id`),
  KEY `technician_id` (`technician_id`),
  CONSTRAINT `maintenance_ibfk_1` FOREIGN KEY (`machine_id`) REFERENCES `machine` (`machine_id`),
  CONSTRAINT `maintenance_ibfk_2` FOREIGN KEY (`technician_id`) REFERENCES `technician` (`technician_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `ai_decision` (
  `decision_id` int NOT NULL AUTO_INCREMENT,
  `machine_id` int NOT NULL,
  `decision_time` datetime NOT NULL,
  `failure_risk` decimal(5,2) NOT NULL,
  `health_score` decimal(5,2) NOT NULL,
  `urgency_score` decimal(5,2) NOT NULL,
  `urgency_level` varchar(20) NOT NULL,
  `recommendation` varchar(255) NOT NULL,
  `model_key` varchar(50) NOT NULL,
  PRIMARY KEY (`decision_id`),
  KEY `machine_id` (`machine_id`),
  CONSTRAINT `ai_decision_ibfk_1` FOREIGN KEY (`machine_id`) REFERENCES `machine` (`machine_id`)
) ENGINE=InnoDB AUTO_INCREMENT=80 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `sensor_reading` (
  `reading_id` int NOT NULL AUTO_INCREMENT,
  `machine_id` int NOT NULL,
  `recorded_at` datetime NOT NULL,
  PRIMARY KEY (`reading_id`),
  KEY `machine_id` (`machine_id`),
  CONSTRAINT `sensor_reading_ibfk_1` FOREIGN KEY (`machine_id`) REFERENCES `machine` (`machine_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `sensor_measurement` (
  `measurement_id` int NOT NULL AUTO_INCREMENT,
  `reading_id` int NOT NULL,
  `sensor_name` varchar(50) NOT NULL,
  `sensor_value` decimal(10,2) NOT NULL,
  `unit` varchar(20) NOT NULL,
  PRIMARY KEY (`measurement_id`),
  KEY `reading_id` (`reading_id`),
  CONSTRAINT `sensor_measurement_ibfk_1` FOREIGN KEY (`reading_id`) REFERENCES `sensor_reading` (`reading_id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `maintenance_requirement` (
  `requirement_id` int NOT NULL AUTO_INCREMENT,
  `maintenance_type` varchar(100) NOT NULL,
  `machine_type_id` int NOT NULL,
  `spare_part_id` int NOT NULL,
  `required_quantity` int NOT NULL,
  `estimated_duration_hours` decimal(5,2) NOT NULL,
  PRIMARY KEY (`requirement_id`),
  KEY `machine_type_id` (`machine_type_id`),
  KEY `spare_part_id` (`spare_part_id`),
  CONSTRAINT `maintenance_requirement_ibfk_1` FOREIGN KEY (`machine_type_id`) REFERENCES `machine_type` (`machine_type_id`),
  CONSTRAINT `maintenance_requirement_ibfk_2` FOREIGN KEY (`spare_part_id`) REFERENCES `spare_part` (`spare_part_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `spare_reservation` (
  `reservation_id` int NOT NULL AUTO_INCREMENT,
  `maintenance_id` int NOT NULL,
  `spare_part_id` int NOT NULL,
  `quantity_reserved` int NOT NULL,
  `reservation_status` varchar(30) NOT NULL,
  PRIMARY KEY (`reservation_id`),
  KEY `maintenance_id` (`maintenance_id`),
  KEY `spare_part_id` (`spare_part_id`),
  CONSTRAINT `spare_reservation_ibfk_1` FOREIGN KEY (`maintenance_id`) REFERENCES `maintenance` (`maintenance_id`),
  CONSTRAINT `spare_reservation_ibfk_2` FOREIGN KEY (`spare_part_id`) REFERENCES `spare_part` (`spare_part_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;
