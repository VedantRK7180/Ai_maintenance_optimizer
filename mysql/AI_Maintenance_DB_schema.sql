-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: ai_maintenance_db
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `ai_decision`
--

DROP TABLE IF EXISTS `ai_decision`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ai_decision`
--

LOCK TABLES `ai_decision` WRITE;
/*!40000 ALTER TABLE `ai_decision` DISABLE KEYS */;
INSERT INTO `ai_decision` VALUES (1,2,'2026-10-03 05:50:50',43.00,57.00,61.84,'MEDIUM','Schedule maintenance soon.','ai4i'),(2,2,'2026-10-03 22:14:35',43.00,57.00,61.84,'MEDIUM','Schedule maintenance soon.','ai4i'),(3,2,'2026-10-03 22:19:25',43.00,57.00,61.84,'MEDIUM','Schedule maintenance soon.','AI4I-RandomForest'),(4,3,'2026-10-03 22:19:25',68.50,31.50,65.00,'HIGH','Schedule maintenance immediately.','AI4I-RandomForest'),(5,2,'2026-10-05 20:18:18',43.00,57.00,61.84,'MEDIUM','Schedule maintenance soon.','AI4I-RandomForest'),(6,3,'2026-10-05 20:18:18',68.50,31.50,65.00,'HIGH','Schedule maintenance immediately.','AI4I-RandomForest'),(7,2,'2026-10-05 23:16:48',43.00,57.00,61.84,'MEDIUM','Schedule maintenance soon.','AI4I-RandomForest'),(8,3,'2026-10-05 23:16:48',68.50,31.50,65.00,'HIGH','Schedule maintenance immediately.','AI4I-RandomForest'),(9,2,'2026-10-05 23:20:28',43.00,57.00,61.84,'MEDIUM','Schedule maintenance soon.','AI4I-RandomForest'),(10,3,'2026-10-05 23:20:29',68.50,31.50,65.00,'HIGH','Schedule maintenance immediately.','AI4I-RandomForest'),(11,5,'2026-10-05 23:20:29',0.33,99.67,50.00,'MEDIUM','Schedule maintenance soon.','Robot-RandomForest'),(12,2,'2026-10-05 23:28:35',43.00,57.00,61.84,'MEDIUM','Schedule maintenance soon.','AI4I-RandomForest'),(13,3,'2026-10-05 23:28:35',68.50,31.50,65.00,'HIGH','Schedule maintenance immediately.','AI4I-RandomForest'),(14,5,'2026-10-05 23:28:36',0.33,99.67,50.00,'MEDIUM','Schedule maintenance soon.','Robot-RandomForest'),(15,9,'2026-10-05 23:45:41',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA_IMS_Bearing'),(16,10,'2026-10-05 23:45:41',61.90,38.10,65.00,'HIGH','Schedule maintenance soon','NASA_IMS_Bearing'),(17,11,'2026-10-05 23:45:41',61.90,38.10,52.18,'MEDIUM','Schedule maintenance soon','NASA_IMS_Bearing'),(18,12,'2026-10-05 23:45:41',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA_IMS_Bearing'),(19,5,'2026-10-05 23:52:10',0.33,99.67,50.00,'MEDIUM','Schedule maintenance soon','Robot-RandomForest'),(20,9,'2026-10-05 23:52:10',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(21,10,'2026-10-05 23:52:10',61.90,38.10,65.00,'HIGH','Schedule maintenance immediately','NASA-IMS-Bearing'),(22,11,'2026-10-05 23:52:10',61.90,38.10,52.18,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(23,12,'2026-10-05 23:52:10',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(24,5,'2026-10-05 23:53:58',0.33,99.67,50.00,'MEDIUM','Schedule maintenance soon','Robot-RandomForest'),(25,9,'2026-10-05 23:53:58',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(26,10,'2026-10-05 23:53:58',61.90,38.10,65.00,'HIGH','Schedule maintenance immediately','NASA-IMS-Bearing'),(27,11,'2026-10-05 23:53:59',61.90,38.10,52.18,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(28,12,'2026-10-05 23:53:59',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(29,2,'2026-10-05 23:56:37',43.00,57.00,61.84,'MEDIUM','Schedule maintenance soon','AI4I-RandomForest'),(30,3,'2026-10-05 23:56:37',68.50,31.50,65.00,'HIGH','Schedule maintenance immediately','AI4I-RandomForest'),(31,5,'2026-10-05 23:56:37',0.33,99.67,50.00,'MEDIUM','Schedule maintenance soon','Robot-RandomForest'),(32,9,'2026-10-05 23:56:37',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(33,10,'2026-10-05 23:56:37',61.90,38.10,65.00,'HIGH','Schedule maintenance immediately','NASA-IMS-Bearing'),(34,11,'2026-10-05 23:56:37',61.90,38.10,52.18,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(35,12,'2026-10-05 23:56:37',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(36,2,'2026-10-06 00:03:14',43.00,57.00,61.84,'MEDIUM','Schedule maintenance soon','AI4I-RandomForest'),(37,3,'2026-10-06 00:03:14',68.50,31.50,65.00,'HIGH','Schedule maintenance immediately','AI4I-RandomForest'),(38,5,'2026-10-06 00:03:15',0.33,99.67,50.00,'MEDIUM','Schedule maintenance soon','Robot-RandomForest'),(39,6,'2026-10-06 00:03:15',25.67,74.33,64.94,'MEDIUM','Schedule maintenance soon','Robot-RandomForest'),(40,9,'2026-10-06 00:03:15',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(41,10,'2026-10-06 00:03:15',61.90,38.10,65.00,'HIGH','Schedule maintenance immediately','NASA-IMS-Bearing'),(42,11,'2026-10-06 00:03:15',61.90,38.10,52.18,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(43,12,'2026-10-06 00:03:15',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(44,2,'2026-10-07 00:42:16',43.00,57.00,61.84,'MEDIUM','Schedule maintenance soon','AI4I-RandomForest'),(45,3,'2026-10-07 00:42:16',68.50,31.50,65.00,'HIGH','Schedule maintenance immediately','AI4I-RandomForest'),(46,5,'2026-10-07 00:42:16',0.33,99.67,50.00,'MEDIUM','Schedule maintenance soon','Robot-RandomForest'),(47,6,'2026-10-07 00:42:17',25.67,74.33,64.94,'MEDIUM','Schedule maintenance soon','Robot-RandomForest'),(48,9,'2026-10-07 00:42:17',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(49,10,'2026-10-07 00:42:17',61.90,38.10,65.00,'HIGH','Schedule maintenance immediately','NASA-IMS-Bearing'),(50,11,'2026-10-07 00:42:17',61.90,38.10,52.18,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(51,12,'2026-10-07 00:42:17',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(52,5,'2026-10-07 00:44:15',0.33,99.67,50.00,'MEDIUM','Schedule maintenance soon','Robot-RandomForest'),(53,6,'2026-10-07 00:44:15',25.67,74.33,64.94,'MEDIUM','Schedule maintenance soon','Robot-RandomForest'),(54,9,'2026-10-07 00:44:15',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(55,10,'2026-10-07 00:44:15',61.90,38.10,65.00,'HIGH','Schedule maintenance immediately','NASA-IMS-Bearing'),(56,11,'2026-10-07 00:44:15',61.90,38.10,52.18,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(57,12,'2026-10-07 00:44:15',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon','NASA-IMS-Bearing'),(58,5,'2026-10-07 00:48:31',0.33,99.67,50.00,'MEDIUM','Schedule maintenance soon.','Robot-RandomForest'),(59,6,'2026-10-07 00:48:31',25.67,74.33,64.94,'MEDIUM','Schedule maintenance soon.','Robot-RandomForest'),(60,9,'2026-10-07 00:48:31',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon.','NASA-IMS-Bearing'),(61,10,'2026-10-07 00:48:31',61.90,38.10,65.00,'HIGH','Schedule maintenance immediately.','NASA-IMS-Bearing'),(62,11,'2026-10-07 00:48:31',61.90,38.10,52.18,'MEDIUM','Schedule maintenance soon.','NASA-IMS-Bearing'),(63,12,'2026-10-07 00:48:31',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon.','NASA-IMS-Bearing'),(64,2,'2026-10-07 00:54:14',43.00,57.00,61.84,'MEDIUM','Schedule maintenance soon.','AI4I-RandomForest'),(65,3,'2026-10-07 00:54:14',68.50,31.50,65.00,'HIGH','Schedule maintenance immediately.','AI4I-RandomForest'),(66,5,'2026-10-07 00:54:14',0.33,99.67,50.00,'MEDIUM','Schedule maintenance soon.','Robot-RandomForest'),(67,6,'2026-10-07 00:54:15',25.67,74.33,64.94,'MEDIUM','Schedule maintenance soon.','Robot-RandomForest'),(68,9,'2026-10-07 00:54:15',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon.','NASA-IMS-Bearing'),(69,10,'2026-10-07 00:54:15',61.90,38.10,65.00,'HIGH','Schedule maintenance immediately.','NASA-IMS-Bearing'),(70,11,'2026-10-07 00:54:15',61.90,38.10,52.18,'MEDIUM','Schedule maintenance soon.','NASA-IMS-Bearing'),(71,12,'2026-10-07 00:54:15',61.90,38.10,63.59,'MEDIUM','Schedule maintenance soon.','NASA-IMS-Bearing'),(72,2,'2026-10-12 22:37:46',43.00,57.00,61.84,'MEDIUM','Schedule maintenance soon.','AI4I-RandomForest'),(73,3,'2026-10-12 22:37:46',68.50,31.50,65.00,'HIGH','Schedule maintenance immediately.','AI4I-RandomForest'),(74,5,'2026-10-12 22:37:47',0.33,99.67,50.00,'MEDIUM','Schedule maintenance soon.','Robot-RandomForest'),(75,6,'2026-10-12 22:37:47',25.67,74.33,64.94,'MEDIUM','Schedule maintenance soon.','Robot-RandomForest'),(76,9,'2026-10-12 22:37:47',61.90,38.10,63.60,'MEDIUM','Schedule maintenance soon.','NASA-IMS-Bearing'),(77,10,'2026-10-12 22:37:47',61.90,38.10,65.00,'HIGH','Schedule maintenance immediately.','NASA-IMS-Bearing'),(78,11,'2026-10-12 22:37:47',61.90,38.10,52.19,'MEDIUM','Schedule maintenance soon.','NASA-IMS-Bearing'),(79,12,'2026-10-12 22:37:47',61.90,38.10,63.60,'MEDIUM','Schedule maintenance soon.','NASA-IMS-Bearing');
/*!40000 ALTER TABLE `ai_decision` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `machine`
--

DROP TABLE IF EXISTS `machine`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `machine`
--

LOCK TABLES `machine` WRITE;
/*!40000 ALTER TABLE `machine` DISABLE KEYS */;
INSERT INTO `machine` VALUES (1,'CNC-101',5200.00,'Medium','High','Normal',1),(2,'CNC-102',7240.00,'High','High','Monitoring',1),(3,'CNC-103',6100.00,'High','Medium','Critical',1),(4,'CNC-104',8300.00,'Critical','High','Normal',1),(5,'ROB-201',4100.00,'High','High','Normal',2),(6,'ROB-202',6750.00,'Critical','High','Monitoring',2),(7,'ROB-203',3200.00,'Medium','Medium','Normal',2),(8,'ROB-204',7800.00,'Critical','High','Critical',2),(9,'ROT-301',5600.00,'High','High','Normal',3),(10,'ROT-302',8900.00,'Critical','High','Monitoring',3),(11,'ROT-303',4700.00,'Medium','Medium','Normal',3),(12,'ROT-304',7200.00,'High','High','Maintenance',3);
/*!40000 ALTER TABLE `machine` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `machine_type`
--

DROP TABLE IF EXISTS `machine_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `machine_type` (
  `machine_type_id` int NOT NULL AUTO_INCREMENT,
  `type_name` varchar(100) NOT NULL,
  `model_key` varchar(50) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`machine_type_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `machine_type`
--

LOCK TABLES `machine_type` WRITE;
/*!40000 ALTER TABLE `machine_type` DISABLE KEYS */;
INSERT INTO `machine_type` VALUES (1,'CNC Machine','ai4i','CNC machine using the AI4I predictive maintenance model'),(2,'Robotic Arm','robot','Industrial robotic arm for predictive maintenance'),(3,'Rotating Equipment','bearing','Rotating equipment using bearing condition data');
/*!40000 ALTER TABLE `machine_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `maintenance`
--

DROP TABLE IF EXISTS `maintenance`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maintenance`
--

LOCK TABLES `maintenance` WRITE;
/*!40000 ALTER TABLE `maintenance` DISABLE KEYS */;
INSERT INTO `maintenance` VALUES (1,2,1,'Preventive Maintenance','2026-10-04','12:00:00','14:00:00','Planned','Medium','AI-optimized schedule generated by Genetic Algorithm.'),(2,3,1,'Spindle Bearing Replacement','2026-10-04','09:00:00','12:00:00','Planned','High','AI-optimized schedule generated by Genetic Algorithm.'),(3,5,NULL,'Robot Motor Inspection',NULL,NULL,NULL,'Blocked','High','Blocked by AI optimization: required spare part unavailable.'),(4,6,2,'Robot Gear Replacement','2026-10-04','10:00:00','14:00:00','Planned','Medium','AI-optimized schedule generated by Genetic Algorithm.'),(5,9,3,'Bearing Inspection','2026-10-04','09:00:00','11:00:00','Planned','High','AI-optimized schedule generated by Genetic Algorithm.'),(6,10,NULL,'Rotating Shaft Replacement',NULL,NULL,NULL,'Blocked','Medium','Blocked by AI optimization: required spare part unavailable.');
/*!40000 ALTER TABLE `maintenance` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `maintenance_requirement`
--

DROP TABLE IF EXISTS `maintenance_requirement`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `maintenance_requirement`
--

LOCK TABLES `maintenance_requirement` WRITE;
/*!40000 ALTER TABLE `maintenance_requirement` DISABLE KEYS */;
INSERT INTO `maintenance_requirement` VALUES (1,'Preventive Maintenance',1,1,1,2.00),(2,'Spindle Bearing Replacement',1,2,1,3.00),(3,'Robot Motor Inspection',2,3,1,3.00),(4,'Robot Gear Replacement',2,4,1,4.00),(5,'Bearing Inspection',3,5,1,2.00),(6,'Rotating Shaft Replacement',3,6,1,4.00);
/*!40000 ALTER TABLE `maintenance_requirement` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sensor_measurement`
--

DROP TABLE IF EXISTS `sensor_measurement`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sensor_measurement`
--

LOCK TABLES `sensor_measurement` WRITE;
/*!40000 ALTER TABLE `sensor_measurement` DISABLE KEYS */;
INSERT INTO `sensor_measurement` VALUES (1,1,'Temperature',75.00,'C'),(2,1,'RPM',1400.00,'rpm'),(3,1,'Torque',70.00,'Nm'),(4,1,'Tool Wear',200.00,'min'),(5,2,'Temperature',85.00,'C'),(6,2,'RPM',1400.00,'rpm'),(7,2,'Torque',70.00,'Nm'),(8,2,'Tool Wear',240.00,'min'),(9,3,'Position',25.00,'degree'),(10,3,'Temperature',66.00,'C'),(11,3,'Voltage',7046.00,'mV'),(12,4,'Position',35.00,'degree'),(13,4,'Temperature',70.00,'C'),(14,4,'Voltage',6980.00,'mV');
/*!40000 ALTER TABLE `sensor_measurement` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sensor_reading`
--

DROP TABLE IF EXISTS `sensor_reading`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sensor_reading` (
  `reading_id` int NOT NULL AUTO_INCREMENT,
  `machine_id` int NOT NULL,
  `recorded_at` datetime NOT NULL,
  PRIMARY KEY (`reading_id`),
  KEY `machine_id` (`machine_id`),
  CONSTRAINT `sensor_reading_ibfk_1` FOREIGN KEY (`machine_id`) REFERENCES `machine` (`machine_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sensor_reading`
--

LOCK TABLES `sensor_reading` WRITE;
/*!40000 ALTER TABLE `sensor_reading` DISABLE KEYS */;
INSERT INTO `sensor_reading` VALUES (1,2,'2026-10-03 05:36:35'),(2,3,'2026-10-03 22:16:57'),(3,5,'2026-10-05 23:18:26'),(4,6,'2026-10-06 00:02:16');
/*!40000 ALTER TABLE `sensor_reading` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `spare_part`
--

DROP TABLE IF EXISTS `spare_part`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `spare_part` (
  `spare_part_id` int NOT NULL AUTO_INCREMENT,
  `part_name` varchar(100) NOT NULL,
  `machine_type_id` int NOT NULL,
  `quantity_available` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`spare_part_id`),
  KEY `machine_type_id` (`machine_type_id`),
  CONSTRAINT `spare_part_ibfk_1` FOREIGN KEY (`machine_type_id`) REFERENCES `machine_type` (`machine_type_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `spare_part`
--

LOCK TABLES `spare_part` WRITE;
/*!40000 ALTER TABLE `spare_part` DISABLE KEYS */;
INSERT INTO `spare_part` VALUES (1,'CNC Cutting Tool',1,4),(2,'CNC Spindle Bearing',1,1),(3,'Robot Motor',2,0),(4,'Robot Gear Assembly',2,1),(5,'Industrial Bearing',3,3),(6,'Rotating Shaft',3,0);
/*!40000 ALTER TABLE `spare_part` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `spare_reservation`
--

DROP TABLE IF EXISTS `spare_reservation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
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
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `spare_reservation`
--

LOCK TABLES `spare_reservation` WRITE;
/*!40000 ALTER TABLE `spare_reservation` DISABLE KEYS */;
INSERT INTO `spare_reservation` VALUES (1,1,1,1,'Reserved'),(2,2,2,1,'Reserved'),(3,1,1,1,'Reserved'),(4,4,4,1,'Reserved'),(5,3,3,1,'Reserved'),(6,6,6,1,'Reserved'),(7,5,5,1,'Reserved');
/*!40000 ALTER TABLE `spare_reservation` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `technician`
--

DROP TABLE IF EXISTS `technician`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `technician` (
  `technician_id` int NOT NULL AUTO_INCREMENT,
  `technician_name` varchar(100) NOT NULL,
  `specialization` varchar(100) NOT NULL,
  `availability_status` varchar(20) NOT NULL,
  PRIMARY KEY (`technician_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `technician`
--

LOCK TABLES `technician` WRITE;
/*!40000 ALTER TABLE `technician` DISABLE KEYS */;
INSERT INTO `technician` VALUES (1,'Rahul Sharma','CNC','Available'),(2,'Aman Patil','Robotics','Available'),(3,'Neha Kulkarni','Rotating Equipment','Available'),(4,'Vivek Joshi','CNC','Available');
/*!40000 ALTER TABLE `technician` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-25 20:52:32
