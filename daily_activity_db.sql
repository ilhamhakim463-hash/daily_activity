-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1:3307
-- Generation Time: Apr 16, 2026 at 09:28 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `daily_activity_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `activity_streaks`
--

CREATE TABLE `activity_streaks` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `current_streak` int(11) DEFAULT 0,
  `longest_streak` int(11) DEFAULT 0,
  `last_active_date` date DEFAULT NULL,
  `total_days` int(11) DEFAULT 0,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `activity_streaks`
--

INSERT INTO `activity_streaks` (`id`, `user_id`, `current_streak`, `longest_streak`, `last_active_date`, `total_days`, `updated_at`) VALUES
(1, 1, 8, 14, '2026-03-10', 43, '2026-03-10 16:10:23'),
(2, 2, 0, 0, NULL, 0, '2026-03-09 04:32:59'),
(3, 3, 0, 0, NULL, 0, '2026-04-03 13:12:50');

-- --------------------------------------------------------

--
-- Table structure for table `adaptive_log`
--

CREATE TABLE `adaptive_log` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `log_date` date NOT NULL,
  `fail_streak` int(11) DEFAULT 0,
  `action_taken` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `currencies`
--

CREATE TABLE `currencies` (
  `code` varchar(10) NOT NULL,
  `name` varchar(50) NOT NULL,
  `symbol` varchar(5) NOT NULL,
  `rate_to_idr` decimal(20,6) DEFAULT 1.000000,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `currencies`
--

INSERT INTO `currencies` (`code`, `name`, `symbol`, `rate_to_idr`, `updated_at`) VALUES
('AUD', 'Australian Dollar', 'A$', 10500.000000, '2026-04-03 09:56:45'),
('EUR', 'Euro', '€', 17500.000000, '2026-04-03 09:56:45'),
('GBP', 'British Pound', '£', 20000.000000, '2026-04-03 09:56:45'),
('IDR', 'Rupiah Indonesia', 'Rp', 1.000000, '2026-04-03 09:56:45'),
('JPY', 'Japanese Yen', '¥', 110.000000, '2026-04-03 09:56:45'),
('MYR', 'Ringgit Malaysia', 'RM', 3500.000000, '2026-04-03 09:56:45'),
('SAR', 'Riyal Saudi Arabia', 'SR', 4200.000000, '2026-04-03 09:56:45'),
('SGD', 'Singapore Dollar', 'S$', 12000.000000, '2026-04-03 09:56:45'),
('USD', 'US Dollar', '$', 16000.000000, '2026-04-03 09:56:45');

-- --------------------------------------------------------

--
-- Table structure for table `daily_focus`
--

CREATE TABLE `daily_focus` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `focus_date` date NOT NULL,
  `rank` tinyint(4) NOT NULL DEFAULT 1,
  `source` varchar(30) NOT NULL,
  `title` varchar(200) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `ref_type` varchar(30) DEFAULT NULL,
  `ref_id` int(11) DEFAULT NULL,
  `is_done` tinyint(1) DEFAULT 0,
  `done_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `daily_focus`
--

INSERT INTO `daily_focus` (`id`, `user_id`, `focus_date`, `rank`, `source`, `title`, `description`, `ref_type`, `ref_id`, `is_done`, `done_at`, `created_at`) VALUES
(1, 1, '2026-04-03', 1, 'milestone_deadline', 'Milestone: Investasi Reksa Dana', 'Bagian dari goal \'Personal Finance\' · Deadline bulan ini', 'milestone', 4, 0, NULL, '2026-04-03 09:57:43'),
(2, 1, '2026-04-03', 2, 'milestone_deadline', 'Milestone: Frontend React', 'Bagian dari goal \'Fullstack Mastery\' · Deadline bulan ini', 'milestone', 2, 0, NULL, '2026-04-03 09:57:43'),
(3, 1, '2026-04-03', 3, 'milestone_deadline', 'Milestone: Cardio 20x', 'Bagian dari goal \'Fitness & Health\' · Deadline bulan ini', 'milestone', 3, 0, NULL, '2026-04-03 09:57:43');

-- --------------------------------------------------------

--
-- Table structure for table `daily_tasks`
--

CREATE TABLE `daily_tasks` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `milestone_id` int(11) DEFAULT NULL,
  `title` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `category` varchar(50) DEFAULT 'general',
  `priority` enum('low','medium','high','urgent') DEFAULT 'medium',
  `status` enum('todo','in_progress','done','cancelled') DEFAULT 'todo',
  `duration_min` int(11) DEFAULT 0,
  `task_date` date DEFAULT curdate(),
  `start_time` time DEFAULT NULL,
  `end_time` time DEFAULT NULL,
  `tags` varchar(255) DEFAULT NULL,
  `completed_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `goal_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `daily_tasks`
--

INSERT INTO `daily_tasks` (`id`, `user_id`, `milestone_id`, `title`, `description`, `category`, `priority`, `status`, `duration_min`, `task_date`, `start_time`, `end_time`, `tags`, `completed_at`, `created_at`, `updated_at`, `goal_id`) VALUES
(1, 1, 1, 'Belajar Flask Route & Blueprint', 'Study session', 'tech', 'high', 'done', 120, '2026-03-09', NULL, NULL, NULL, '2026-03-09 02:16:22', '2026-03-09 02:14:34', '2026-03-09 02:16:22', NULL),
(2, 1, 1, 'Coding REST API endpoint', 'Implementasi', 'tech', 'medium', 'done', 90, '2026-03-09', NULL, NULL, NULL, '2026-03-09 02:16:25', '2026-03-09 02:14:34', '2026-03-09 02:16:25', NULL),
(3, 1, 3, 'Lari pagi 5km', 'Cardio session', 'health', 'medium', 'done', 45, '2026-03-09', NULL, NULL, NULL, '2026-03-09 02:16:26', '2026-03-09 02:14:34', '2026-03-09 02:16:26', NULL),
(4, 1, 1, 'Belajar Flask Route & Blueprint', 'Study session', 'tech', 'high', 'done', 120, '2026-03-08', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(5, 1, 1, 'Coding REST API endpoint', 'Implementasi', 'tech', 'medium', 'todo', 90, '2026-03-08', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(6, 1, 3, 'Lari pagi 5km', 'Cardio session', 'health', 'medium', 'done', 45, '2026-03-08', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(7, 1, 1, 'Belajar Flask Route & Blueprint', 'Study session', 'tech', 'high', 'done', 120, '2026-03-07', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(8, 1, 1, 'Coding REST API endpoint', 'Implementasi', 'tech', 'medium', 'done', 90, '2026-03-07', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(9, 1, 3, 'Lari pagi 5km', 'Cardio session', 'health', 'medium', 'done', 45, '2026-03-07', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(10, 1, 1, 'Belajar Flask Route & Blueprint', 'Study session', 'tech', 'high', 'done', 120, '2026-03-06', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(11, 1, 1, 'Coding REST API endpoint', 'Implementasi', 'tech', 'medium', 'done', 90, '2026-03-06', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(12, 1, 3, 'Lari pagi 5km', 'Cardio session', 'health', 'medium', 'done', 45, '2026-03-06', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(13, 1, 1, 'Belajar Flask Route & Blueprint', 'Study session', 'tech', 'high', 'done', 120, '2026-03-05', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(14, 1, 1, 'Coding REST API endpoint', 'Implementasi', 'tech', 'medium', 'done', 90, '2026-03-05', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(15, 1, 3, 'Lari pagi 5km', 'Cardio session', 'health', 'medium', 'done', 45, '2026-03-05', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(16, 1, 1, 'Belajar Flask Route & Blueprint', 'Study session', 'tech', 'high', 'done', 120, '2026-03-04', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(17, 1, 1, 'Coding REST API endpoint', 'Implementasi', 'tech', 'medium', 'done', 90, '2026-03-04', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(18, 1, 3, 'Lari pagi 5km', 'Cardio session', 'health', 'medium', 'done', 45, '2026-03-04', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(19, 1, 1, 'Belajar Flask Route & Blueprint', 'Study session', 'tech', 'high', 'done', 120, '2026-03-03', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(20, 1, 1, 'Coding REST API endpoint', 'Implementasi', 'tech', 'medium', 'done', 90, '2026-03-03', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(21, 1, 3, 'Lari pagi 5km', 'Cardio session', 'health', 'medium', 'done', 45, '2026-03-03', NULL, NULL, NULL, NULL, '2026-03-09 02:14:34', '2026-03-09 02:14:34', NULL),
(22, 1, NULL, 'ff', '', 'general', 'low', 'todo', 25, '2026-03-10', NULL, NULL, 'ff', NULL, '2026-03-10 16:10:05', '2026-03-10 16:10:24', NULL),
(23, 2, NULL, 'dd', '', 'general', 'medium', 'todo', 25, '2026-03-11', NULL, NULL, 'ddd', NULL, '2026-03-11 07:16:46', '2026-03-11 07:16:46', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `fixed_expenses`
--

CREATE TABLE `fixed_expenses` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `title` varchar(200) NOT NULL,
  `emoji` varchar(10) DEFAULT '?',
  `amount` decimal(20,2) NOT NULL,
  `currency` varchar(10) DEFAULT 'IDR',
  `category` varchar(30) DEFAULT 'lainnya',
  `billing_day` tinyint(4) DEFAULT 1,
  `is_active` tinyint(1) DEFAULT 1,
  `notes` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `ghost_snapshots`
--

CREATE TABLE `ghost_snapshots` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `week_start` date NOT NULL,
  `day_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`day_data`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `goals`
--

CREATE TABLE `goals` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `title` varchar(200) NOT NULL,
  `description` text DEFAULT NULL,
  `year` int(11) NOT NULL,
  `category` varchar(50) DEFAULT 'general',
  `color` varchar(7) DEFAULT '#6366f1',
  `icon` varchar(50) DEFAULT 'target',
  `is_active` tinyint(1) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `goals`
--

INSERT INTO `goals` (`id`, `user_id`, `title`, `description`, `year`, `category`, `color`, `icon`, `is_active`, `created_at`) VALUES
(1, 1, 'Fullstack Mastery', 'Menguasai pengembangan fullstack', 2026, 'tech', '#6366f1', 'code', 1, '2026-03-09 02:14:34'),
(2, 1, 'Fitness & Health', 'Hidup sehat dan bugar', 2026, 'health', '#10b981', 'heart', 1, '2026-03-09 02:14:34'),
(3, 1, 'Personal Finance', 'Literasi dan manajemen keuangan', 2026, 'finance', '#f59e0b', 'trending-up', 1, '2026-03-09 02:14:34'),
(4, 2, 'bisa menggunakan php murni', 'bisa mengusai php murni ditahun ini ', 2026, 'personal', '#64f2d5', 'target', 1, '2026-03-09 09:15:01');

-- --------------------------------------------------------

--
-- Table structure for table `investments`
--

CREATE TABLE `investments` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `goal_id` int(11) DEFAULT NULL,
  `title` varchar(200) NOT NULL,
  `type` varchar(30) DEFAULT 'lainnya',
  `emoji` varchar(10) DEFAULT '?',
  `buy_price` decimal(20,6) NOT NULL,
  `units` decimal(20,6) DEFAULT 1.000000,
  `currency` varchar(10) DEFAULT 'IDR',
  `buy_date` date NOT NULL,
  `current_price` decimal(20,6) DEFAULT NULL,
  `price_updated_at` timestamp NULL DEFAULT NULL,
  `platform` varchar(100) DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `investment_logs`
--

CREATE TABLE `investment_logs` (
  `id` int(11) NOT NULL,
  `investment_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `type` varchar(20) DEFAULT 'price_update',
  `price` decimal(20,6) NOT NULL,
  `units` decimal(20,6) DEFAULT 0.000000,
  `log_date` date NOT NULL,
  `note` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `isq_evening`
--

CREATE TABLE `isq_evening` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `entry_date` date NOT NULL,
  `energy_level` tinyint(4) DEFAULT 3,
  `mood` varchar(10) DEFAULT NULL,
  `mood_label` varchar(50) DEFAULT NULL,
  `intention_done` tinyint(4) DEFAULT 0,
  `micro_journal` text DEFAULT NULL,
  `highlight` varchar(255) DEFAULT NULL,
  `gratitude_close` varchar(255) DEFAULT NULL,
  `isq_score` tinyint(4) DEFAULT 0,
  `isq_mode` varchar(20) DEFAULT 'steady',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `isq_evening`
--

INSERT INTO `isq_evening` (`id`, `user_id`, `entry_date`, `energy_level`, `mood`, `mood_label`, `intention_done`, `micro_journal`, `highlight`, `gratitude_close`, `isq_score`, `isq_mode`, `created_at`) VALUES
(1, 1, '2026-03-11', 4, '', '', 0, '', '', '', 40, 'struggling', '2026-03-11 00:53:33');

-- --------------------------------------------------------

--
-- Table structure for table `isq_morning`
--

CREATE TABLE `isq_morning` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `entry_date` date NOT NULL,
  `energy_level` tinyint(4) DEFAULT 3,
  `mood` varchar(10) DEFAULT NULL,
  `mood_label` varchar(50) DEFAULT NULL,
  `gratitude_1` varchar(255) DEFAULT NULL,
  `gratitude_2` varchar(255) DEFAULT NULL,
  `gratitude_3` varchar(255) DEFAULT NULL,
  `word_of_day` varchar(50) DEFAULT NULL,
  `intention_1` varchar(255) DEFAULT NULL,
  `intention_2` varchar(255) DEFAULT NULL,
  `intention_3` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `isq_morning`
--

INSERT INTO `isq_morning` (`id`, `user_id`, `entry_date`, `energy_level`, `mood`, `mood_label`, `gratitude_1`, `gratitude_2`, `gratitude_3`, `word_of_day`, `intention_1`, `intention_2`, `intention_3`, `created_at`) VALUES
(1, 1, '2026-03-10', 3, '🎯', 'Focused', 'kesehatn', 'kenikmatan', 'bangun pagi', 'Berani', 'jongging', 'upgrade skill php', 'ibadah tepat waktu', '2026-03-10 16:06:34');

-- --------------------------------------------------------

--
-- Table structure for table `login_logs`
--

CREATE TABLE `login_logs` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `action` varchar(50) NOT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `detail` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `login_logs`
--

INSERT INTO `login_logs` (`id`, `user_id`, `action`, `ip_address`, `detail`, `created_at`) VALUES
(1, 1, 'login_success', '127.0.0.1', '', '2026-03-11 13:54:51'),
(2, 1, 'login_success', '127.0.0.1', '', '2026-03-11 14:15:05'),
(3, 2, 'login_success', '127.0.0.1', '', '2026-03-11 14:15:45'),
(4, 1, 'login_success', '127.0.0.1', '', '2026-03-11 14:19:20'),
(5, 1, 'login_success', '127.0.0.1', '', '2026-03-11 14:24:34'),
(6, 1, 'login_success', '127.0.0.1', '', '2026-03-11 14:41:35'),
(7, 1, 'login_success', '127.0.0.1', '', '2026-03-11 14:43:11'),
(8, 2, 'login_success', '127.0.0.1', '', '2026-03-11 14:44:00'),
(9, 2, 'login_success', '127.0.0.1', '', '2026-03-11 18:57:38'),
(10, 2, 'login_success', '127.0.0.1', '', '2026-03-11 20:39:41'),
(11, 1, 'login_failed', '127.0.0.1', 'attempt 1/5', '2026-03-31 09:20:40'),
(12, 1, 'login_failed', '127.0.0.1', 'attempt 2/5', '2026-04-02 10:00:38'),
(13, 1, 'login_failed', '127.0.0.1', 'attempt 3/5', '2026-04-02 10:01:07'),
(14, 1, 'login_failed', '127.0.0.1', 'attempt 4/5', '2026-04-02 10:01:24'),
(15, 2, 'login_success', '127.0.0.1', '', '2026-04-02 10:03:15'),
(16, 1, 'login_failed', '127.0.0.1', 'attempt 0/5', '2026-04-02 10:04:40'),
(17, 1, 'login_success', '127.0.0.1', '', '2026-04-02 10:17:22'),
(18, 1, 'login_success', '127.0.0.1', '', '2026-04-02 20:59:52'),
(19, 1, 'login_success', '127.0.0.1', '', '2026-04-03 20:11:36'),
(20, 1, 'login_success', '127.0.0.1', '', '2026-04-03 20:16:36');

-- --------------------------------------------------------

--
-- Table structure for table `milestones`
--

CREATE TABLE `milestones` (
  `id` int(11) NOT NULL,
  `goal_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `title` varchar(200) NOT NULL,
  `description` text DEFAULT NULL,
  `month` int(11) NOT NULL,
  `year` int(11) NOT NULL,
  `target_value` decimal(10,2) DEFAULT 100.00,
  `unit` varchar(30) DEFAULT 'percent',
  `is_completed` tinyint(1) DEFAULT 0,
  `completed_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `milestones`
--

INSERT INTO `milestones` (`id`, `goal_id`, `user_id`, `title`, `description`, `month`, `year`, `target_value`, `unit`, `is_completed`, `completed_at`, `created_at`) VALUES
(1, 1, 1, 'Backend Python Flask', 'API & Database', 3, 2026, 100.00, 'percent', 0, NULL, '2026-03-09 02:14:34'),
(2, 1, 1, 'Frontend React', 'UI & State Management', 3, 2026, 100.00, 'percent', 0, NULL, '2026-03-09 02:14:34'),
(3, 2, 1, 'Cardio 20x', 'Lari & Bersepeda', 3, 2026, 100.00, 'percent', 0, NULL, '2026-03-09 02:14:34'),
(4, 3, 1, 'Investasi Reksa Dana', 'Mulai investasi rutin', 3, 2026, 100.00, 'percent', 0, NULL, '2026-03-09 02:14:34');

-- --------------------------------------------------------

--
-- Table structure for table `push_subscriptions`
--

CREATE TABLE `push_subscriptions` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `endpoint` text NOT NULL,
  `p256dh` varchar(255) DEFAULT NULL,
  `auth_key` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `quick_notes`
--

CREATE TABLE `quick_notes` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `content` text DEFAULT NULL,
  `color` varchar(7) DEFAULT '#6366f1',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `note_date` date NOT NULL DEFAULT '2024-01-01'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `quick_notes`
--

INSERT INTO `quick_notes` (`id`, `user_id`, `content`, `color`, `created_at`, `updated_at`, `note_date`) VALUES
(1, 2, 'gggg', '#f43f5e', '2026-03-11 14:43:49', '2026-04-02 13:56:34', '2026-03-11'),
(2, 2, 'gggg', '#10b981', '2026-03-11 14:43:57', '2026-04-02 13:56:34', '2026-03-11'),
(3, 2, '', '#f43f5e', '2026-03-12 14:38:46', '2026-04-02 13:56:34', '2026-03-12'),
(4, 2, '', '#06b6d4', '2026-03-12 14:38:50', '2026-04-02 13:56:34', '2026-03-12'),
(5, 2, '', '#06b6d4', '2026-03-12 14:38:51', '2026-04-02 13:56:34', '2026-03-12'),
(6, 2, '', '#06b6d4', '2026-03-12 14:38:51', '2026-04-02 13:56:34', '2026-03-12'),
(7, 2, '', '#06b6d4', '2026-03-12 14:38:51', '2026-04-02 13:56:34', '2026-03-12'),
(8, 2, '', '#f59e0b', '2026-03-12 14:38:52', '2026-04-02 13:56:34', '2026-03-12'),
(9, 2, '', '#f43f5e', '2026-03-12 14:38:53', '2026-04-02 13:56:34', '2026-03-12'),
(10, 2, '', '#06b6d4', '2026-03-12 14:38:53', '2026-04-02 13:56:34', '2026-03-12');

-- --------------------------------------------------------

--
-- Table structure for table `reminders`
--

CREATE TABLE `reminders` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `title` varchar(200) NOT NULL,
  `emoji` varchar(10) DEFAULT '?',
  `remind_time` time NOT NULL,
  `repeat_type` enum('daily','weekdays','weekend','weekly','custom') DEFAULT 'daily',
  `repeat_days` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`repeat_days`)),
  `snooze_minutes` int(11) DEFAULT 30,
  `is_active` tinyint(1) DEFAULT 1,
  `has_quantity` tinyint(1) DEFAULT 0,
  `quantity_target` decimal(8,2) DEFAULT NULL,
  `quantity_unit` varchar(30) DEFAULT NULL,
  `category` varchar(50) DEFAULT 'general',
  `color` varchar(7) DEFAULT '#6366f1',
  `sort_order` int(11) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `goal_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `reminders`
--

INSERT INTO `reminders` (`id`, `user_id`, `title`, `emoji`, `remind_time`, `repeat_type`, `repeat_days`, `snooze_minutes`, `is_active`, `has_quantity`, `quantity_target`, `quantity_unit`, `category`, `color`, `sort_order`, `created_at`, `updated_at`, `goal_id`) VALUES
(1, 1, 'Sholat Subuh', '🌅', '04:30:00', 'daily', NULL, 10, 0, 0, NULL, NULL, 'ibadah', '#6366f1', 0, '2026-04-03 06:02:17', '2026-04-03 06:02:35', NULL),
(4, 1, 'Sholat Maghrib', '🌆', '18:00:00', 'daily', NULL, 10, 1, 0, NULL, NULL, 'ibadah', '#6366f1', 0, '2026-04-03 06:02:17', '2026-04-03 06:02:17', NULL),
(5, 1, 'Sholat Isya', '🌙', '19:30:00', 'daily', NULL, 15, 1, 0, NULL, NULL, 'ibadah', '#6366f1', 0, '2026-04-03 06:02:17', '2026-04-03 06:02:17', NULL),
(6, 1, 'Baca Al-Quran', '📖', '05:00:00', 'daily', NULL, 30, 0, 1, 1.00, 'juz', 'ibadah', '#10b981', 0, '2026-04-03 06:02:17', '2026-04-03 06:02:37', NULL),
(7, 1, 'Dzikir Pagi', '🌿', '06:00:00', 'daily', NULL, 20, 0, 0, NULL, NULL, 'ibadah', '#10b981', 0, '2026-04-03 06:02:17', '2026-04-03 06:02:38', NULL),
(8, 1, 'Dzikir Malam', '✨', '21:00:00', 'daily', NULL, 20, 1, 0, NULL, NULL, 'ibadah', '#8b5cf6', 0, '2026-04-03 06:02:17', '2026-04-03 06:02:17', NULL);

-- --------------------------------------------------------

--
-- Table structure for table `reminder_challenge_logs`
--

CREATE TABLE `reminder_challenge_logs` (
  `id` int(11) NOT NULL,
  `challenge_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `log_date` date NOT NULL,
  `completed_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `reminder_groups`
--

CREATE TABLE `reminder_groups` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `description` text DEFAULT NULL,
  `emoji` varchar(10) DEFAULT '?',
  `created_by` int(11) NOT NULL,
  `invite_code` varchar(8) NOT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `reminder_group_challenges`
--

CREATE TABLE `reminder_group_challenges` (
  `id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  `title` varchar(200) NOT NULL,
  `emoji` varchar(10) DEFAULT '?',
  `description` text DEFAULT NULL,
  `remind_time` time NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1,
  `created_by` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `reminder_group_members`
--

CREATE TABLE `reminder_group_members` (
  `id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `role` enum('owner','admin','member') DEFAULT 'member',
  `joined_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `reminder_logs`
--

CREATE TABLE `reminder_logs` (
  `id` int(11) NOT NULL,
  `reminder_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `log_date` date NOT NULL,
  `completed_at` timestamp NULL DEFAULT NULL,
  `quantity_done` decimal(8,2) DEFAULT NULL,
  `snoozed_until` timestamp NULL DEFAULT NULL,
  `skipped` tinyint(1) DEFAULT 0,
  `note` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `reminder_streaks`
--

CREATE TABLE `reminder_streaks` (
  `id` int(11) NOT NULL,
  `reminder_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `current_streak` int(11) DEFAULT 0,
  `longest_streak` int(11) DEFAULT 0,
  `total_done` int(11) DEFAULT 0,
  `last_done_date` date DEFAULT NULL,
  `tier` varchar(20) DEFAULT 'pemula',
  `tier_color` varchar(7) DEFAULT '#888780',
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `reminder_templates`
--

CREATE TABLE `reminder_templates` (
  `id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `category` varchar(50) DEFAULT 'custom',
  `emoji` varchar(10) DEFAULT '?',
  `template_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL CHECK (json_valid(`template_data`)),
  `is_builtin` tinyint(1) DEFAULT 0,
  `use_count` int(11) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `reminder_templates`
--

INSERT INTO `reminder_templates` (`id`, `user_id`, `name`, `description`, `category`, `emoji`, `template_data`, `is_builtin`, `use_count`, `created_at`) VALUES
(1, NULL, 'Paket Ibadah', 'Sholat 5 waktu, Al-Quran, dan dzikir harian', 'ibadah', '🕌', '[{\"title\": \"Sholat Subuh\", \"emoji\": \"\\ud83c\\udf05\", \"remind_time\": \"04:30\", \"snooze_minutes\": 10, \"category\": \"ibadah\", \"color\": \"#6366f1\"}, {\"title\": \"Sholat Dzuhur\", \"emoji\": \"\\u2600\\ufe0f\", \"remind_time\": \"12:00\", \"snooze_minutes\": 15, \"category\": \"ibadah\", \"color\": \"#6366f1\"}, {\"title\": \"Sholat Ashar\", \"emoji\": \"\\ud83c\\udf24\", \"remind_time\": \"15:30\", \"snooze_minutes\": 15, \"category\": \"ibadah\", \"color\": \"#6366f1\"}, {\"title\": \"Sholat Maghrib\", \"emoji\": \"\\ud83c\\udf06\", \"remind_time\": \"18:00\", \"snooze_minutes\": 10, \"category\": \"ibadah\", \"color\": \"#6366f1\"}, {\"title\": \"Sholat Isya\", \"emoji\": \"\\ud83c\\udf19\", \"remind_time\": \"19:30\", \"snooze_minutes\": 15, \"category\": \"ibadah\", \"color\": \"#6366f1\"}, {\"title\": \"Baca Al-Quran\", \"emoji\": \"\\ud83d\\udcd6\", \"remind_time\": \"05:00\", \"snooze_minutes\": 30, \"has_quantity\": true, \"quantity_target\": 1, \"quantity_unit\": \"juz\", \"category\": \"ibadah\", \"color\": \"#10b981\"}, {\"title\": \"Dzikir Pagi\", \"emoji\": \"\\ud83c\\udf3f\", \"remind_time\": \"06:00\", \"snooze_minutes\": 20, \"category\": \"ibadah\", \"color\": \"#10b981\"}, {\"title\": \"Dzikir Malam\", \"emoji\": \"\\u2728\", \"remind_time\": \"21:00\", \"snooze_minutes\": 20, \"category\": \"ibadah\", \"color\": \"#8b5cf6\"}]', 1, 1, '2026-04-02 13:56:34'),
(2, NULL, 'Paket Kesehatan', 'Olahraga, hidrasi, tidur, dan vitamin', 'kesehatan', '💪', '[{\"title\": \"Minum Air Pagi\", \"emoji\": \"\\ud83d\\udca7\", \"remind_time\": \"07:00\", \"snooze_minutes\": 30, \"has_quantity\": true, \"quantity_target\": 2, \"quantity_unit\": \"gelas\", \"category\": \"kesehatan\", \"color\": \"#0ea5e9\"}, {\"title\": \"Minum Air Siang\", \"emoji\": \"\\ud83d\\udca7\", \"remind_time\": \"12:00\", \"snooze_minutes\": 30, \"has_quantity\": true, \"quantity_target\": 2, \"quantity_unit\": \"gelas\", \"category\": \"kesehatan\", \"color\": \"#0ea5e9\"}, {\"title\": \"Minum Air Sore\", \"emoji\": \"\\ud83d\\udca7\", \"remind_time\": \"16:00\", \"snooze_minutes\": 30, \"has_quantity\": true, \"quantity_target\": 2, \"quantity_unit\": \"gelas\", \"category\": \"kesehatan\", \"color\": \"#0ea5e9\"}, {\"title\": \"Olahraga\", \"emoji\": \"\\ud83c\\udfc3\", \"remind_time\": \"06:00\", \"snooze_minutes\": 30, \"has_quantity\": true, \"quantity_target\": 30, \"quantity_unit\": \"menit\", \"category\": \"kesehatan\", \"color\": \"#f59e0b\"}, {\"title\": \"Minum Vitamin\", \"emoji\": \"\\ud83d\\udc8a\", \"remind_time\": \"08:00\", \"snooze_minutes\": 60, \"category\": \"kesehatan\", \"color\": \"#ec4899\"}, {\"title\": \"Tidur Tepat Waktu\", \"emoji\": \"\\ud83d\\ude34\", \"remind_time\": \"22:00\", \"snooze_minutes\": 30, \"category\": \"kesehatan\", \"color\": \"#8b5cf6\"}]', 1, 0, '2026-04-02 13:56:34'),
(3, NULL, 'Paket Produktivitas', 'Review pagi, fokus kerja, dan refleksi malam', 'produktivitas', '⚡', '[{\"title\": \"Review Tasks Pagi\", \"emoji\": \"\\ud83d\\udccb\", \"remind_time\": \"07:30\", \"snooze_minutes\": 15, \"category\": \"produktivitas\", \"color\": \"#6366f1\"}, {\"title\": \"Deep Work Pagi\", \"emoji\": \"\\ud83c\\udfaf\", \"remind_time\": \"08:00\", \"snooze_minutes\": 30, \"has_quantity\": true, \"quantity_target\": 90, \"quantity_unit\": \"menit\", \"category\": \"produktivitas\", \"color\": \"#f59e0b\"}, {\"title\": \"Cek Progress Siang\", \"emoji\": \"\\ud83d\\udcca\", \"remind_time\": \"13:00\", \"snooze_minutes\": 30, \"category\": \"produktivitas\", \"color\": \"#6366f1\"}, {\"title\": \"Baca Buku\", \"emoji\": \"\\ud83d\\udcda\", \"remind_time\": \"20:00\", \"snooze_minutes\": 30, \"has_quantity\": true, \"quantity_target\": 20, \"quantity_unit\": \"halaman\", \"category\": \"produktivitas\", \"color\": \"#10b981\"}, {\"title\": \"Jurnal Malam\", \"emoji\": \"\\ud83d\\udcdd\", \"remind_time\": \"21:30\", \"snooze_minutes\": 30, \"category\": \"produktivitas\", \"color\": \"#8b5cf6\"}, {\"title\": \"Review Hari Ini\", \"emoji\": \"\\ud83c\\udf19\", \"remind_time\": \"22:00\", \"snooze_minutes\": 20, \"category\": \"produktivitas\", \"color\": \"#8b5cf6\"}]', 1, 0, '2026-04-02 13:56:34');

-- --------------------------------------------------------

--
-- Table structure for table `savings_goals`
--

CREATE TABLE `savings_goals` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `goal_id` int(11) DEFAULT NULL,
  `title` varchar(200) NOT NULL,
  `emoji` varchar(10) DEFAULT '?',
  `target_amount` decimal(20,2) NOT NULL,
  `currency` varchar(10) DEFAULT 'IDR',
  `period` enum('weekly','monthly','custom') DEFAULT 'weekly',
  `period_amount` decimal(20,2) DEFAULT 0.00,
  `start_date` date NOT NULL,
  `target_date` date DEFAULT NULL,
  `color` varchar(7) DEFAULT '#10b981',
  `is_active` tinyint(1) DEFAULT 1,
  `is_completed` tinyint(1) DEFAULT 0,
  `completed_at` timestamp NULL DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `saving_logs`
--

CREATE TABLE `saving_logs` (
  `id` int(11) NOT NULL,
  `savings_goal_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `amount` decimal(20,2) NOT NULL,
  `type` enum('deposit','withdrawal','adjustment') DEFAULT 'deposit',
  `currency` varchar(10) DEFAULT 'IDR',
  `log_date` date NOT NULL,
  `note` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `saving_streaks`
--

CREATE TABLE `saving_streaks` (
  `id` int(11) NOT NULL,
  `savings_goal_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `current_streak` int(11) DEFAULT 0,
  `longest_streak` int(11) DEFAULT 0,
  `total_periods` int(11) DEFAULT 0,
  `last_period` varchar(10) DEFAULT NULL,
  `tier` varchar(20) DEFAULT 'pemula',
  `tier_color` varchar(7) DEFAULT '#888780',
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `time_capsules`
--

CREATE TABLE `time_capsules` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `message` text NOT NULL,
  `open_date` date NOT NULL,
  `is_opened` tinyint(1) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `full_name` varchar(100) DEFAULT NULL,
  `avatar_url` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `theme_pref` varchar(255) DEFAULT 'dark',
  `onboarded` tinyint(1) DEFAULT 0,
  `is_admin` tinyint(1) DEFAULT 0,
  `failed_attempts` int(11) DEFAULT 0,
  `locked_until` datetime DEFAULT NULL,
  `last_login` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `username`, `email`, `password`, `full_name`, `avatar_url`, `created_at`, `updated_at`, `theme_pref`, `onboarded`, `is_admin`, `failed_attempts`, `locked_until`, `last_login`) VALUES
(1, 'admin', 'admin@example.com', 'pbkdf2$N3Irhdl9sEYU6udcDPAGDGHoPqK5l9XEAAeNmWpThio=$7XzojkLvelTjoXwO4jKiiFfj+rejdyd1gyu99eVmSzU=', 'Admin User', NULL, '2026-03-09 02:14:34', '2026-04-03 13:16:36', 'light', 1, 1, 0, NULL, '2026-04-03 20:16:36'),
(2, 'dani', 'dani@gmail.com', 'pbkdf2$d2DvSpRzqkNKEknm3f0yNxsmnxHz68DIJZbUeU5L4gc=$cKcMOvv2GXwaeuDRCO2fKLdz4rUDNcMK2cFQTbj1Sak=', 'dani', '/static/uploads/avatars/2_9cfafaed.png', '2026-03-09 04:32:59', '2026-04-02 03:03:15', 'light', 1, 0, 0, NULL, '2026-04-02 10:03:15'),
(3, '@ilham', 'ilham@gmail.com', 'pbkdf2$Lxo6yHRCOSV2jq8ooV8GwdB7PSQ38ZUjX8ta4c2yyT8=$tmCgpocgYQgpW0HTNgUGcwnXKwc0fPAA7CYudnNmEqU=', 'ilham', NULL, '2026-04-03 13:12:50', '2026-04-03 13:16:17', 'light', 0, 0, 0, NULL, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `user_archetype`
--

CREATE TABLE `user_archetype` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `archetype` varchar(50) DEFAULT 'explorer',
  `quiz_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`quiz_data`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `user_moods`
--

CREATE TABLE `user_moods` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `mood` varchar(10) NOT NULL,
  `mood_label` varchar(50) DEFAULT NULL,
  `mood_date` date NOT NULL,
  `note` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `user_xp`
--

CREATE TABLE `user_xp` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `total_xp` int(11) DEFAULT 0,
  `level` tinyint(4) DEFAULT 1,
  `level_title` varchar(50) DEFAULT 'Pemula',
  `level_color` varchar(7) DEFAULT '#888780',
  `xp_to_next` int(11) DEFAULT 100,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `weekly_letters`
--

CREATE TABLE `weekly_letters` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `week_number` int(11) NOT NULL,
  `year` int(11) NOT NULL,
  `letter` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `weekly_reviews`
--

CREATE TABLE `weekly_reviews` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `week_start` date NOT NULL,
  `week_end` date NOT NULL,
  `tasks_done` int(11) DEFAULT 0,
  `tasks_total` int(11) DEFAULT 0,
  `reminders_done` int(11) DEFAULT 0,
  `reminders_total` int(11) DEFAULT 0,
  `avg_mood` decimal(4,2) DEFAULT NULL,
  `streaks_gained` int(11) DEFAULT 0,
  `streaks_lost` int(11) DEFAULT 0,
  `saving_amount` decimal(20,2) DEFAULT 0.00,
  `goal_progress` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`goal_progress`)),
  `top_streak` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`top_streak`)),
  `summary_text` text DEFAULT NULL,
  `is_read` tinyint(1) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `weekly_targets`
--

CREATE TABLE `weekly_targets` (
  `id` int(11) NOT NULL,
  `milestone_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `week_number` int(11) NOT NULL,
  `year` int(11) NOT NULL,
  `target_hours` decimal(5,2) DEFAULT 0.00,
  `target_tasks` int(11) DEFAULT 0,
  `notes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `xp_logs`
--

CREATE TABLE `xp_logs` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `xp_amount` int(11) NOT NULL,
  `source` varchar(50) NOT NULL,
  `description` varchar(200) DEFAULT NULL,
  `ref_id` int(11) DEFAULT NULL,
  `earned_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `activity_streaks`
--
ALTER TABLE `activity_streaks`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `user_id` (`user_id`);

--
-- Indexes for table `adaptive_log`
--
ALTER TABLE `adaptive_log`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `currencies`
--
ALTER TABLE `currencies`
  ADD PRIMARY KEY (`code`);

--
-- Indexes for table `daily_focus`
--
ALTER TABLE `daily_focus`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_focus` (`user_id`,`focus_date`,`rank`),
  ADD KEY `idx_focus_date` (`user_id`,`focus_date`);

--
-- Indexes for table `daily_tasks`
--
ALTER TABLE `daily_tasks`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `milestone_id` (`milestone_id`),
  ADD KEY `fk_task_goal` (`goal_id`);

--
-- Indexes for table `fixed_expenses`
--
ALTER TABLE `fixed_expenses`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `ghost_snapshots`
--
ALTER TABLE `ghost_snapshots`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_user_week` (`user_id`,`week_start`);

--
-- Indexes for table `goals`
--
ALTER TABLE `goals`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `investments`
--
ALTER TABLE `investments`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `goal_id` (`goal_id`);

--
-- Indexes for table `investment_logs`
--
ALTER TABLE `investment_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `idx_invlog_inv` (`investment_id`,`log_date`);

--
-- Indexes for table `isq_evening`
--
ALTER TABLE `isq_evening`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_user_date` (`user_id`,`entry_date`);

--
-- Indexes for table `isq_morning`
--
ALTER TABLE `isq_morning`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_user_date` (`user_id`,`entry_date`);

--
-- Indexes for table `login_logs`
--
ALTER TABLE `login_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_user_id` (`user_id`),
  ADD KEY `idx_created_at` (`created_at`);

--
-- Indexes for table `milestones`
--
ALTER TABLE `milestones`
  ADD PRIMARY KEY (`id`),
  ADD KEY `goal_id` (`goal_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `push_subscriptions`
--
ALTER TABLE `push_subscriptions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_user_endpoint` (`user_id`,`endpoint`(200));

--
-- Indexes for table `quick_notes`
--
ALTER TABLE `quick_notes`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `reminders`
--
ALTER TABLE `reminders`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_rem_user_active` (`user_id`,`is_active`),
  ADD KEY `idx_rem_user_time` (`user_id`,`remind_time`),
  ADD KEY `fk_rem_goal` (`goal_id`);

--
-- Indexes for table `reminder_challenge_logs`
--
ALTER TABLE `reminder_challenge_logs`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_chlog` (`challenge_id`,`user_id`,`log_date`),
  ADD KEY `idx_chlog_date` (`challenge_id`,`log_date`),
  ADD KEY `idx_chlog_user` (`user_id`,`log_date`);

--
-- Indexes for table `reminder_groups`
--
ALTER TABLE `reminder_groups`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `invite_code` (`invite_code`),
  ADD KEY `created_by` (`created_by`),
  ADD KEY `idx_group_invite` (`invite_code`);

--
-- Indexes for table `reminder_group_challenges`
--
ALTER TABLE `reminder_group_challenges`
  ADD PRIMARY KEY (`id`),
  ADD KEY `created_by` (`created_by`),
  ADD KEY `idx_challenge_group` (`group_id`,`is_active`);

--
-- Indexes for table `reminder_group_members`
--
ALTER TABLE `reminder_group_members`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_group_user` (`group_id`,`user_id`),
  ADD KEY `idx_gmem_user` (`user_id`);

--
-- Indexes for table `reminder_logs`
--
ALTER TABLE `reminder_logs`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_log_per_day` (`reminder_id`,`log_date`),
  ADD KEY `idx_log_user_date` (`user_id`,`log_date`),
  ADD KEY `idx_log_reminder` (`reminder_id`,`log_date`);

--
-- Indexes for table `reminder_streaks`
--
ALTER TABLE `reminder_streaks`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `reminder_id` (`reminder_id`),
  ADD KEY `idx_rstreak_user` (`user_id`);

--
-- Indexes for table `reminder_templates`
--
ALTER TABLE `reminder_templates`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `idx_tpl_category` (`category`,`is_builtin`);

--
-- Indexes for table `savings_goals`
--
ALTER TABLE `savings_goals`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `goal_id` (`goal_id`);

--
-- Indexes for table `saving_logs`
--
ALTER TABLE `saving_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_savlog_goal` (`savings_goal_id`,`log_date`),
  ADD KEY `idx_savlog_user` (`user_id`,`log_date`);

--
-- Indexes for table `saving_streaks`
--
ALTER TABLE `saving_streaks`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `savings_goal_id` (`savings_goal_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `time_capsules`
--
ALTER TABLE `time_capsules`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indexes for table `user_archetype`
--
ALTER TABLE `user_archetype`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `user_id` (`user_id`);

--
-- Indexes for table `user_moods`
--
ALTER TABLE `user_moods`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_user_date` (`user_id`,`mood_date`);

--
-- Indexes for table `user_xp`
--
ALTER TABLE `user_xp`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `user_id` (`user_id`);

--
-- Indexes for table `weekly_letters`
--
ALTER TABLE `weekly_letters`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_user_week` (`user_id`,`week_number`,`year`);

--
-- Indexes for table `weekly_reviews`
--
ALTER TABLE `weekly_reviews`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_review` (`user_id`,`week_start`);

--
-- Indexes for table `weekly_targets`
--
ALTER TABLE `weekly_targets`
  ADD PRIMARY KEY (`id`),
  ADD KEY `milestone_id` (`milestone_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `xp_logs`
--
ALTER TABLE `xp_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_xp_user` (`user_id`,`earned_at`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `activity_streaks`
--
ALTER TABLE `activity_streaks`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `adaptive_log`
--
ALTER TABLE `adaptive_log`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `daily_focus`
--
ALTER TABLE `daily_focus`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `daily_tasks`
--
ALTER TABLE `daily_tasks`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=24;

--
-- AUTO_INCREMENT for table `fixed_expenses`
--
ALTER TABLE `fixed_expenses`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `ghost_snapshots`
--
ALTER TABLE `ghost_snapshots`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `goals`
--
ALTER TABLE `goals`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `investments`
--
ALTER TABLE `investments`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `investment_logs`
--
ALTER TABLE `investment_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `isq_evening`
--
ALTER TABLE `isq_evening`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `isq_morning`
--
ALTER TABLE `isq_morning`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `login_logs`
--
ALTER TABLE `login_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=21;

--
-- AUTO_INCREMENT for table `milestones`
--
ALTER TABLE `milestones`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `push_subscriptions`
--
ALTER TABLE `push_subscriptions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `quick_notes`
--
ALTER TABLE `quick_notes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT for table `reminders`
--
ALTER TABLE `reminders`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT for table `reminder_challenge_logs`
--
ALTER TABLE `reminder_challenge_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `reminder_groups`
--
ALTER TABLE `reminder_groups`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `reminder_group_challenges`
--
ALTER TABLE `reminder_group_challenges`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `reminder_group_members`
--
ALTER TABLE `reminder_group_members`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `reminder_logs`
--
ALTER TABLE `reminder_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `reminder_streaks`
--
ALTER TABLE `reminder_streaks`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `reminder_templates`
--
ALTER TABLE `reminder_templates`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `savings_goals`
--
ALTER TABLE `savings_goals`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `saving_logs`
--
ALTER TABLE `saving_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `saving_streaks`
--
ALTER TABLE `saving_streaks`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `time_capsules`
--
ALTER TABLE `time_capsules`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `user_archetype`
--
ALTER TABLE `user_archetype`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `user_moods`
--
ALTER TABLE `user_moods`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `user_xp`
--
ALTER TABLE `user_xp`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `weekly_letters`
--
ALTER TABLE `weekly_letters`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `weekly_reviews`
--
ALTER TABLE `weekly_reviews`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `weekly_targets`
--
ALTER TABLE `weekly_targets`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `xp_logs`
--
ALTER TABLE `xp_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `activity_streaks`
--
ALTER TABLE `activity_streaks`
  ADD CONSTRAINT `activity_streaks_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `adaptive_log`
--
ALTER TABLE `adaptive_log`
  ADD CONSTRAINT `adaptive_log_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `daily_focus`
--
ALTER TABLE `daily_focus`
  ADD CONSTRAINT `daily_focus_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `daily_tasks`
--
ALTER TABLE `daily_tasks`
  ADD CONSTRAINT `daily_tasks_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `daily_tasks_ibfk_2` FOREIGN KEY (`milestone_id`) REFERENCES `milestones` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_task_goal` FOREIGN KEY (`goal_id`) REFERENCES `goals` (`id`) ON DELETE SET NULL;

--
-- Constraints for table `fixed_expenses`
--
ALTER TABLE `fixed_expenses`
  ADD CONSTRAINT `fixed_expenses_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `ghost_snapshots`
--
ALTER TABLE `ghost_snapshots`
  ADD CONSTRAINT `ghost_snapshots_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `goals`
--
ALTER TABLE `goals`
  ADD CONSTRAINT `goals_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `investments`
--
ALTER TABLE `investments`
  ADD CONSTRAINT `investments_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `investments_ibfk_2` FOREIGN KEY (`goal_id`) REFERENCES `goals` (`id`) ON DELETE SET NULL;

--
-- Constraints for table `investment_logs`
--
ALTER TABLE `investment_logs`
  ADD CONSTRAINT `investment_logs_ibfk_1` FOREIGN KEY (`investment_id`) REFERENCES `investments` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `investment_logs_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `isq_evening`
--
ALTER TABLE `isq_evening`
  ADD CONSTRAINT `isq_evening_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `isq_morning`
--
ALTER TABLE `isq_morning`
  ADD CONSTRAINT `isq_morning_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `milestones`
--
ALTER TABLE `milestones`
  ADD CONSTRAINT `milestones_ibfk_1` FOREIGN KEY (`goal_id`) REFERENCES `goals` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `milestones_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `push_subscriptions`
--
ALTER TABLE `push_subscriptions`
  ADD CONSTRAINT `push_subscriptions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `quick_notes`
--
ALTER TABLE `quick_notes`
  ADD CONSTRAINT `quick_notes_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `reminders`
--
ALTER TABLE `reminders`
  ADD CONSTRAINT `fk_rem_goal` FOREIGN KEY (`goal_id`) REFERENCES `goals` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `reminders_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `reminder_challenge_logs`
--
ALTER TABLE `reminder_challenge_logs`
  ADD CONSTRAINT `reminder_challenge_logs_ibfk_1` FOREIGN KEY (`challenge_id`) REFERENCES `reminder_group_challenges` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `reminder_challenge_logs_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `reminder_groups`
--
ALTER TABLE `reminder_groups`
  ADD CONSTRAINT `reminder_groups_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `reminder_group_challenges`
--
ALTER TABLE `reminder_group_challenges`
  ADD CONSTRAINT `reminder_group_challenges_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `reminder_groups` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `reminder_group_challenges_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `reminder_group_members`
--
ALTER TABLE `reminder_group_members`
  ADD CONSTRAINT `reminder_group_members_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `reminder_groups` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `reminder_group_members_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `reminder_logs`
--
ALTER TABLE `reminder_logs`
  ADD CONSTRAINT `reminder_logs_ibfk_1` FOREIGN KEY (`reminder_id`) REFERENCES `reminders` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `reminder_logs_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `reminder_streaks`
--
ALTER TABLE `reminder_streaks`
  ADD CONSTRAINT `reminder_streaks_ibfk_1` FOREIGN KEY (`reminder_id`) REFERENCES `reminders` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `reminder_streaks_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `reminder_templates`
--
ALTER TABLE `reminder_templates`
  ADD CONSTRAINT `reminder_templates_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Constraints for table `savings_goals`
--
ALTER TABLE `savings_goals`
  ADD CONSTRAINT `savings_goals_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `savings_goals_ibfk_2` FOREIGN KEY (`goal_id`) REFERENCES `goals` (`id`) ON DELETE SET NULL;

--
-- Constraints for table `saving_logs`
--
ALTER TABLE `saving_logs`
  ADD CONSTRAINT `saving_logs_ibfk_1` FOREIGN KEY (`savings_goal_id`) REFERENCES `savings_goals` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `saving_logs_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `saving_streaks`
--
ALTER TABLE `saving_streaks`
  ADD CONSTRAINT `saving_streaks_ibfk_1` FOREIGN KEY (`savings_goal_id`) REFERENCES `savings_goals` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `saving_streaks_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `time_capsules`
--
ALTER TABLE `time_capsules`
  ADD CONSTRAINT `time_capsules_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `user_archetype`
--
ALTER TABLE `user_archetype`
  ADD CONSTRAINT `user_archetype_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `user_moods`
--
ALTER TABLE `user_moods`
  ADD CONSTRAINT `user_moods_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `user_xp`
--
ALTER TABLE `user_xp`
  ADD CONSTRAINT `user_xp_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `weekly_letters`
--
ALTER TABLE `weekly_letters`
  ADD CONSTRAINT `weekly_letters_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `weekly_reviews`
--
ALTER TABLE `weekly_reviews`
  ADD CONSTRAINT `weekly_reviews_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `weekly_targets`
--
ALTER TABLE `weekly_targets`
  ADD CONSTRAINT `weekly_targets_ibfk_1` FOREIGN KEY (`milestone_id`) REFERENCES `milestones` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `weekly_targets_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `xp_logs`
--
ALTER TABLE `xp_logs`
  ADD CONSTRAINT `xp_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
