//
//  AppLogger.swift
//  llamacpp-gui
//
//  File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/gui-macos/Sources/Logging/AppLogger.swift
//  Description: Centralized os.log wrapper with file:line context; also prints to stdout for development.
//  Author: Libor Ballaty <libor@arionetworks.com>
//  Created: 2026-06-22
//

import Foundation
import os.log

// Centralized logging utility
enum AppLogger {
    private static let logger = Logger(subsystem: "com.llamacpp.manager", category: "GUI")

    enum LogLevel {
        case debug
        case info
        case warning
        case error
    }

    static func log(_ message: String, level: LogLevel = .info, file: String = #file, function: String = #function, line: Int = #line) {
        let filename = (file as NSString).lastPathComponent
        let formattedMessage = "[\(filename):\(line)] \(function) - \(message)"

        switch level {
        case .debug:
            logger.debug("\(formattedMessage)")
        case .info:
            logger.info("\(formattedMessage)")
        case .warning:
            logger.warning("\(formattedMessage)")
        case .error:
            logger.error("\(formattedMessage)")
        }

        // Additional console logging for development
        print("[LlamaCPP Manager] \(formattedMessage)")
    }
}
