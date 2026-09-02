import SwiftUI
import UIKit

// MARK: - Access / Key system

private enum AccessEntryMode: String, CaseIterable, Identifiable {
    case user = "Usuário"
    case moderator = "Moderador"

    var id: String { rawValue }
}

private enum KeyDuration: String, Codable, CaseIterable, Identifiable {
    case oneHour
    case oneDay
    case fifteenDays
    case thirtyDays

    var id: String { rawValue }

    var title: String {
        switch self {
        case .oneHour: return "1 hora"
        case .oneDay: return "1 dia"
        case .fifteenDays: return "15 dias"
        case .thirtyDays: return "30 dias"
        }
    }

    var shortTitle: String {
        switch self {
        case .oneHour: return "1H"
        case .oneDay: return "1D"
        case .fifteenDays: return "15D"
        case .thirtyDays: return "30D"
        }
    }

    var seconds: TimeInterval {
        switch self {
        case .oneHour: return 60 * 60
        case .oneDay: return 24 * 60 * 60
        case .fifteenDays: return 15 * 24 * 60 * 60
        case .thirtyDays: return 30 * 24 * 60 * 60
        }
    }
}

private struct LicenseKeyRecord: Codable, Identifiable, Equatable {
    let id: UUID
    let code: String
    let duration: KeyDuration
    let createdAt: Date
    var activatedAt: Date?
    var deviceID: String?
    var revoked: Bool

    var expiresAt: Date? {
        guard let activatedAt else { return nil }
        return activatedAt.addingTimeInterval(duration.seconds)
    }

    func remaining(at date: Date = Date()) -> TimeInterval? {
        guard let expiresAt else { return nil }
        return max(0, expiresAt.timeIntervalSince(date))
    }

    func isExpired(at date: Date = Date()) -> Bool {
        guard let expiresAt else { return false }
        return expiresAt <= date
    }
}

private final class LocalKeyStore: ObservableObject {
    private static let recordsStorageKey = "rnzw.keys.records.v1"
    private static let activeKeyStorageKey = "rnzw.keys.active.code.v1"
    private static let moderatorPINStorageKey = "rnzw.moderator.pin.v1"

    @Published private(set) var records: [LicenseKeyRecord] = []
    @Published private(set) var activeKeyCode: String?
    @Published var message: String?

    init() {
        load()
    }

    var activeRecord: LicenseKeyRecord? {
        guard let activeKeyCode else { return nil }
        return records.first(where: { $0.code == activeKeyCode })
    }

    var hasValidActiveKey: Bool {
        guard let record = activeRecord else { return false }
        return !record.revoked && !record.isExpired() && record.deviceID == Self.currentDeviceID
    }

    var moderatorPIN: String {
        let stored = UserDefaults.standard.string(forKey: Self.moderatorPINStorageKey)
        return (stored?.isEmpty == false) ? stored! : "3105"
    }

    @discardableResult
    func generate(duration: KeyDuration) -> LicenseKeyRecord {
        var code: String
        repeat {
            code = Self.makeKeyCode()
        } while records.contains(where: { $0.code == code })

        let record = LicenseKeyRecord(
            id: UUID(),
            code: code,
            duration: duration,
            createdAt: Date(),
            activatedAt: nil,
            deviceID: nil,
            revoked: false
        )
        records.insert(record, at: 0)
        save()
        return record
    }

    func activate(code rawCode: String) -> Bool {
        let code = Self.normalize(rawCode)
        guard let index = records.firstIndex(where: { $0.code == code }) else {
            message = "Key inválida."
            return false
        }

        if records[index].revoked {
            message = "Essa key foi revogada."
            return false
        }

        if records[index].isExpired() {
            message = "Essa key expirou."
            return false
        }

        if let boundDevice = records[index].deviceID,
           boundDevice != Self.currentDeviceID {
            message = "Essa key já está vinculada a outro aparelho."
            return false
        }

        if records[index].activatedAt == nil {
            records[index].activatedAt = Date()
            records[index].deviceID = Self.currentDeviceID
        }

        activeKeyCode = records[index].code
        UserDefaults.standard.set(activeKeyCode, forKey: Self.activeKeyStorageKey)
        message = nil
        save()
        return true
    }

    func revoke(_ record: LicenseKeyRecord) {
        guard let index = records.firstIndex(where: { $0.id == record.id }) else { return }
        records[index].revoked = true
        if activeKeyCode == record.code {
            logoutUser()
        }
        save()
    }

    func delete(_ record: LicenseKeyRecord) {
        if activeKeyCode == record.code {
            logoutUser()
        }
        records.removeAll(where: { $0.id == record.id })
        save()
    }

    func logoutUser() {
        activeKeyCode = nil
        UserDefaults.standard.removeObject(forKey: Self.activeKeyStorageKey)
    }

    func validateModerator(pin: String) -> Bool {
        pin.trimmingCharacters(in: .whitespacesAndNewlines) == moderatorPIN
    }

    func updateModeratorPIN(_ newPIN: String) -> Bool {
        let cleaned = newPIN.trimmingCharacters(in: .whitespacesAndNewlines)
        guard cleaned.count >= 4 else {
            message = "O código do moderador precisa ter pelo menos 4 caracteres."
            return false
        }
        UserDefaults.standard.set(cleaned, forKey: Self.moderatorPINStorageKey)
        message = "Código do moderador atualizado."
        return true
    }

    private func load() {
        if let data = UserDefaults.standard.data(forKey: Self.recordsStorageKey),
           let decoded = try? JSONDecoder().decode([LicenseKeyRecord].self, from: data) {
            records = decoded
        }
        activeKeyCode = UserDefaults.standard.string(forKey: Self.activeKeyStorageKey)

        // Clear an invalid remembered session without deleting the key itself.
        if let activeKeyCode,
           let record = records.first(where: { $0.code == activeKeyCode }),
           (record.revoked || record.isExpired() || record.deviceID != Self.currentDeviceID) {
            self.activeKeyCode = nil
            UserDefaults.standard.removeObject(forKey: Self.activeKeyStorageKey)
        }
    }

    private func save() {
        guard let data = try? JSONEncoder().encode(records) else { return }
        UserDefaults.standard.set(data, forKey: Self.recordsStorageKey)
    }

    private static var currentDeviceID: String {
        UIDevice.current.identifierForVendor?.uuidString ?? "unknown-device"
    }

    private static func normalize(_ value: String) -> String {
        value
            .uppercased()
            .filter { $0.isLetter || $0.isNumber }
            .splitEvery(4)
            .joined(separator: "-")
    }

    private static func makeKeyCode() -> String {
        let alphabet = Array("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        let body = String((0..<12).compactMap { _ in alphabet.randomElement() })
        return "RNZW-" + body.splitEvery(4).joined(separator: "-")
    }
}

private extension String {
    func splitEvery(_ length: Int) -> [String] {
        guard length > 0 else { return [self] }
        var output: [String] = []
        var cursor = startIndex
        while cursor < endIndex {
            let end = index(cursor, offsetBy: length, limitedBy: endIndex) ?? endIndex
            output.append(String(self[cursor..<end]))
            cursor = end
        }
        return output
    }
}

// MARK: - Root

struct ContentView: View {
    @StateObject private var keyStore = LocalKeyStore()
    @State private var moderatorAuthenticated = false

    var body: some View {
        Group {
            if moderatorAuthenticated {
                ModeratorRootView(keyStore: keyStore) {
                    moderatorAuthenticated = false
                }
            } else if keyStore.hasValidActiveKey {
                UserRootView(keyStore: keyStore)
            } else {
                AccessGateView(keyStore: keyStore) {
                    moderatorAuthenticated = true
                }
            }
        }
        .tint(AppTheme.accent)
    }
}

// MARK: - Login / activation

private struct AccessGateView: View {
    @ObservedObject var keyStore: LocalKeyStore
    let onModeratorAuthenticated: () -> Void

    @State private var mode: AccessEntryMode = .user
    @State private var keyText = ""
    @State private var moderatorPIN = ""
    @State private var showModeratorError = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    Spacer(minLength: 28)

                    VStack(spacing: 12) {
                        AppLogo(size: 72)
                        Text("3105")
                            .font(.system(size: 30, weight: .bold, design: .rounded))
                        Text("Acesso ao aplicativo")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }

                    Picker("Tipo de acesso", selection: $mode) {
                        ForEach(AccessEntryMode.allCases) { option in
                            Text(option.rawValue).tag(option)
                        }
                    }
                    .pickerStyle(.segmented)

                    Group {
                        if mode == .user {
                            userLogin
                        } else {
                            moderatorLogin
                        }
                    }
                    .padding(18)
                    .background(
                        Color(uiColor: .secondarySystemBackground),
                        in: RoundedRectangle(cornerRadius: 20, style: .continuous)
                    )
                }
                .padding(.horizontal, 20)
                .frame(maxWidth: 560)
                .frame(maxWidth: .infinity)
            }
            .background(Color(uiColor: .systemGroupedBackground))
        }
    }

    private var userLogin: some View {
        VStack(alignment: .leading, spacing: 14) {
            Label("Ativar key", systemImage: "key.fill")
                .font(.headline)

            TextField("RNZW-XXXX-XXXX-XXXX", text: $keyText)
                .textInputAutocapitalization(.characters)
                .autocorrectionDisabled()
                .font(.body.monospaced())
                .padding(.horizontal, 14)
                .frame(height: 50)
                .background(Color(uiColor: .tertiarySystemFill), in: RoundedRectangle(cornerRadius: 12))
                .onChange(of: keyText) { newValue in
                    let upper = newValue.uppercased()
                    if upper != newValue { keyText = upper }
                    keyStore.message = nil
                }

            if let message = keyStore.message {
                Label(message, systemImage: "exclamationmark.circle.fill")
                    .font(.caption)
                    .foregroundStyle(.red)
            }

            Button {
                _ = keyStore.activate(code: keyText)
            } label: {
                Label("Entrar", systemImage: "arrow.right.circle.fill")
                    .fontWeight(.semibold)
                    .frame(maxWidth: .infinity)
                    .frame(height: 48)
            }
            .buttonStyle(.borderedProminent)
            .disabled(keyText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
        }
    }

    private var moderatorLogin: some View {
        VStack(alignment: .leading, spacing: 14) {
            Label("Área do moderador", systemImage: "person.badge.key.fill")
                .font(.headline)

            SecureField("Código do moderador", text: $moderatorPIN)
                .textContentType(.password)
                .padding(.horizontal, 14)
                .frame(height: 50)
                .background(Color(uiColor: .tertiarySystemFill), in: RoundedRectangle(cornerRadius: 12))
                .onChange(of: moderatorPIN) { _ in showModeratorError = false }
                .onSubmit(authenticateModerator)

            if showModeratorError {
                Label("Código de moderador incorreto.", systemImage: "xmark.circle.fill")
                    .font(.caption)
                    .foregroundStyle(.red)
            }

            Button(action: authenticateModerator) {
                Label("Acessar painel", systemImage: "lock.open.fill")
                    .fontWeight(.semibold)
                    .frame(maxWidth: .infinity)
                    .frame(height: 48)
            }
            .buttonStyle(.borderedProminent)
            .disabled(moderatorPIN.isEmpty)
        }
    }

    private func authenticateModerator() {
        guard keyStore.validateModerator(pin: moderatorPIN) else {
            showModeratorError = true
            return
        }
        moderatorPIN = ""
        showModeratorError = false
        onModeratorAuthenticated()
    }
}

// MARK: - User

private struct UserRootView: View {
    @ObservedObject var keyStore: LocalKeyStore

    var body: some View {
        TabView {
            PatchProjectsView(managementEnabled: false, displayTitle: "Arquivos")
                .tabItem {
                    Label("Arquivos", systemImage: "folder.fill")
                }

            UserMenuView(keyStore: keyStore)
                .tabItem {
                    Label("Menu", systemImage: "square.grid.2x2.fill")
                }
        }
    }
}

private struct UserMenuView: View {
    @EnvironmentObject private var appState: AppState
    @ObservedObject var keyStore: LocalKeyStore

    var body: some View {
        NavigationStack {
            List {
                if let record = keyStore.activeRecord {
                    Section("Sua key") {
                        TimelineView(.periodic(from: .now, by: 1)) { context in
                            HStack(spacing: 12) {
                                AppRowIcon(systemName: "timer", tint: .green)
                                VStack(alignment: .leading, spacing: 3) {
                                    Text("Tempo restante")
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                    Text(remainingText(record, at: context.date))
                                        .font(.title3.bold().monospacedDigit())
                                }
                                Spacer()
                            }
                            .padding(.vertical, 4)
                        }

                        LabeledContent("Plano", value: record.duration.title)
                        LabeledContent("Key", value: record.code)
                        if let expiresAt = record.expiresAt {
                            LabeledContent("Expira em", value: expiresAt.formatted(date: .numeric, time: .shortened))
                        }
                    }
                }

                Section("Informações") {
                    Label {
                        LabeledContent("Desenvolvedor", value: "RNZWSTORE")
                    } icon: {
                        Image(systemName: "hammer.fill")
                    }

                    HStack {
                        Label("Segurança", systemImage: "checkmark.shield.fill")
                        Spacer()
                        Text(keyStore.hasValidActiveKey ? "Key ativa" : "Sem acesso")
                            .foregroundStyle(keyStore.hasValidActiveKey ? Color.green : Color.red)
                    }

                    HStack {
                        Label("Compatibilidade", systemImage: "iphone")
                        Spacer()
                        Text(appState.isSupported ? "Compatível" : "Não verificado")
                            .foregroundStyle(appState.isSupported ? Color.green : Color.orange)
                    }
                }

                Section {
                    Button(role: .destructive) {
                        keyStore.logoutUser()
                    } label: {
                        Label("Sair da conta", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                }
            }
            .navigationTitle("Menu")
        }
    }

    private func remainingText(_ record: LicenseKeyRecord, at date: Date) -> String {
        guard let remaining = record.remaining(at: date), remaining > 0 else {
            return "EXPIRADA"
        }
        let seconds = Int(remaining)
        let days = seconds / 86_400
        let hours = (seconds % 86_400) / 3_600
        let minutes = (seconds % 3_600) / 60
        let secs = seconds % 60
        if days > 0 {
            return String(format: "%dd %02dh %02dm %02ds", days, hours, minutes, secs)
        }
        return String(format: "%02dh %02dm %02ds", hours, minutes, secs)
    }
}

// MARK: - Moderator

private struct ModeratorRootView: View {
    @ObservedObject var keyStore: LocalKeyStore
    let onLogout: () -> Void

    var body: some View {
        TabView {
            KeyGeneratorView(keyStore: keyStore, onLogout: onLogout)
                .tabItem {
                    Label("Keys", systemImage: "key.fill")
                }

            PatchProjectsView(managementEnabled: true, displayTitle: "Arquivos")
                .tabItem {
                    Label("Arquivos", systemImage: "folder.badge.gearshape")
                }
        }
    }
}

private struct KeyGeneratorView: View {
    @ObservedObject var keyStore: LocalKeyStore
    let onLogout: () -> Void

    @State private var selectedDuration: KeyDuration = .oneDay
    @State private var lastGeneratedKey: LicenseKeyRecord?
    @State private var newModeratorPIN = ""
    @State private var copiedCode: String?

    var body: some View {
        NavigationStack {
            List {
                Section("Gerador de key") {
                    Picker("Duração", selection: $selectedDuration) {
                        ForEach(KeyDuration.allCases) { duration in
                            Text(duration.title).tag(duration)
                        }
                    }

                    HStack(spacing: 8) {
                        ForEach(KeyDuration.allCases) { duration in
                            Button(duration.shortTitle) {
                                selectedDuration = duration
                            }
                            .buttonStyle(.bordered)
                            .tint(selectedDuration == duration ? AppTheme.accent : .secondary)
                        }
                    }

                    Button {
                        let generated = keyStore.generate(duration: selectedDuration)
                        lastGeneratedKey = generated
                        copiedCode = nil
                    } label: {
                        Label("Gerar key de \(selectedDuration.title)", systemImage: "plus.circle.fill")
                            .fontWeight(.semibold)
                    }

                    if let lastGeneratedKey {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Última key gerada")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Text(lastGeneratedKey.code)
                                .font(.body.bold().monospaced())
                                .textSelection(.enabled)
                            Button {
                                copy(lastGeneratedKey.code)
                            } label: {
                                Label(copiedCode == lastGeneratedKey.code ? "Copiada" : "Copiar key",
                                      systemImage: copiedCode == lastGeneratedKey.code ? "checkmark" : "doc.on.doc")
                            }
                            .buttonStyle(.bordered)
                        }
                        .padding(.vertical, 6)
                    }
                }

                Section("Keys geradas") {
                    if keyStore.records.isEmpty {
                        VStack(spacing: 8) {
                            Image(systemName: "key.horizontal")
                                .font(.title2)
                                .foregroundStyle(.secondary)
                            Text("Nenhuma key")
                                .font(.headline)
                            Text("Gere a primeira key usando uma das durações acima.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .multilineTextAlignment(.center)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 20)
                    } else {
                        ForEach(keyStore.records) { record in
                            KeyRecordRow(record: record, copiedCode: copiedCode) {
                                copy(record.code)
                            } onRevoke: {
                                keyStore.revoke(record)
                            } onDelete: {
                                keyStore.delete(record)
                            }
                        }
                    }
                }

                Section("Moderador") {
                    SecureField("Novo código do moderador", text: $newModeratorPIN)
                    Button("Alterar código") {
                        if keyStore.updateModeratorPIN(newModeratorPIN) {
                            newModeratorPIN = ""
                        }
                    }
                    .disabled(newModeratorPIN.count < 4)

                    if let message = keyStore.message {
                        Text(message)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Button(role: .destructive, action: onLogout) {
                        Label("Sair do painel", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                }
            }
            .navigationTitle("Moderador")
        }
    }

    private func copy(_ code: String) {
        UIPasteboard.general.string = code
        copiedCode = code
    }
}

private struct KeyRecordRow: View {
    let record: LicenseKeyRecord
    let copiedCode: String?
    let onCopy: () -> Void
    let onRevoke: () -> Void
    let onDelete: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            AppRowIcon(systemName: statusIcon, tint: statusColor)

            VStack(alignment: .leading, spacing: 4) {
                Text(record.code)
                    .font(.subheadline.weight(.semibold).monospaced())
                    .lineLimit(1)
                    .minimumScaleFactor(0.72)
                Text(statusText)
                    .font(.caption)
                    .foregroundStyle(statusColor)
            }

            Spacer(minLength: 8)

            Menu {
                Button(action: onCopy) {
                    Label(copiedCode == record.code ? "Copiada" : "Copiar", systemImage: "doc.on.doc")
                }
                if !record.revoked {
                    Button(role: .destructive, action: onRevoke) {
                        Label("Revogar", systemImage: "nosign")
                    }
                }
                Button(role: .destructive, action: onDelete) {
                    Label("Excluir", systemImage: "trash")
                }
            } label: {
                Image(systemName: "ellipsis.circle")
                    .font(.title3)
            }
        }
        .padding(.vertical, 4)
    }

    private var statusText: String {
        if record.revoked { return "Revogada • \(record.duration.title)" }
        if record.isExpired() { return "Expirada • \(record.duration.title)" }
        guard let remaining = record.remaining() else {
            return "Aguardando ativação • \(record.duration.title)"
        }
        let hours = Int(remaining / 3600)
        if hours >= 24 {
            return "Ativa • \(max(1, hours / 24))d restantes"
        }
        return "Ativa • \(max(1, hours))h restantes"
    }

    private var statusColor: Color {
        if record.revoked || record.isExpired() { return .red }
        if record.activatedAt == nil { return .orange }
        return .green
    }

    private var statusIcon: String {
        if record.revoked { return "nosign" }
        if record.isExpired() { return "clock.badge.xmark" }
        if record.activatedAt == nil { return "key.horizontal" }
        return "checkmark.shield.fill"
    }
}
