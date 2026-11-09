from ..database import now

DDL = (
    "CREATE TABLE circle_rooms(party_id TEXT PRIMARY KEY REFERENCES travel_parties(id),mode TEXT NOT NULL,desired_count INTEGER NOT NULL,tags TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL)",
    "CREATE TABLE circle_member_invitations(id TEXT PRIMARY KEY,party_id TEXT NOT NULL REFERENCES travel_parties(id),invitee_id TEXT NOT NULL REFERENCES users(id),inviter_id TEXT NOT NULL REFERENCES users(id),status TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL)",
    "CREATE UNIQUE INDEX circle_pending_person ON circle_member_invitations(party_id,invitee_id) WHERE status='pending'",
    "CREATE INDEX circle_invitee ON circle_member_invitations(invitee_id,status)",
    "CREATE TABLE circle_assistant_turns(id TEXT PRIMARY KEY,party_id TEXT NOT NULL REFERENCES travel_parties(id),author_id TEXT NOT NULL REFERENCES users(id),body TEXT NOT NULL,created_at TEXT NOT NULL)",
    "CREATE INDEX circle_turn_party ON circle_assistant_turns(party_id,created_at)",
    "CREATE TABLE circle_provider_invitations(id TEXT PRIMARY KEY,party_id TEXT NOT NULL REFERENCES travel_parties(id),provider_id TEXT NOT NULL REFERENCES providers(id),inviter_id TEXT NOT NULL REFERENCES users(id),snapshot TEXT NOT NULL,status TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,consultation_id TEXT UNIQUE REFERENCES consultations(id),created_at TEXT NOT NULL,accepted_at TEXT)",
    "CREATE UNIQUE INDEX circle_active_provider ON circle_provider_invitations(party_id) WHERE status IN ('pending','accepted')",
    "CREATE TABLE circle_proposals(id TEXT PRIMARY KEY,invitation_id TEXT NOT NULL REFERENCES circle_provider_invitations(id),version INTEGER NOT NULL,body TEXT NOT NULL,created_by TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,UNIQUE(invitation_id,version))",
    "CREATE TABLE circle_confirmations(proposal_id TEXT NOT NULL REFERENCES circle_proposals(id),role TEXT NOT NULL CHECK(role IN ('traveler','provider')),user_id TEXT NOT NULL REFERENCES users(id),confirmed_at TEXT NOT NULL,PRIMARY KEY(proposal_id,role))",
    "CREATE TRIGGER circle_member_added AFTER INSERT ON travel_party_members BEGIN UPDATE circle_rooms SET version=version+1 WHERE party_id=NEW.party_id; END",
    "CREATE TRIGGER circle_member_removed AFTER DELETE ON travel_party_members BEGIN UPDATE circle_rooms SET version=version+1 WHERE party_id=OLD.party_id; END",
    "CREATE TRIGGER circle_invitation_added AFTER INSERT ON circle_member_invitations BEGIN UPDATE circle_rooms SET version=version+1 WHERE party_id=NEW.party_id; END",
    "CREATE TRIGGER circle_invitation_changed AFTER UPDATE ON circle_member_invitations BEGIN UPDATE circle_rooms SET version=version+1 WHERE party_id=NEW.party_id; END",
    "CREATE TRIGGER circle_provider_added AFTER INSERT ON circle_provider_invitations BEGIN UPDATE circle_rooms SET version=version+1 WHERE party_id=NEW.party_id; END",
    "CREATE TRIGGER circle_provider_changed AFTER UPDATE ON circle_provider_invitations BEGIN UPDATE circle_rooms SET version=version+1 WHERE party_id=NEW.party_id; END",
    "CREATE TRIGGER circle_provider_revoked AFTER UPDATE OF status ON circle_provider_invitations WHEN NEW.status IN ('cancelled','declined','closed') BEGIN UPDATE consultations SET status='closed',version=version+1 WHERE id=NEW.consultation_id; UPDATE plan_selections SET status='closed' WHERE id IN (SELECT selection_id FROM consultations WHERE id=NEW.consultation_id); END",
    "CREATE TRIGGER circle_consultation_closed AFTER UPDATE OF status ON consultations WHEN NEW.status='closed' BEGIN UPDATE circle_provider_invitations SET status='closed',version=version+1 WHERE consultation_id=NEW.id AND status='accepted'; END",
    "CREATE TRIGGER circle_party_closed AFTER UPDATE OF status ON travel_parties WHEN NEW.status='closed' BEGIN UPDATE circle_rooms SET version=version+1 WHERE party_id=NEW.id; UPDATE circle_member_invitations SET status='cancelled',version=version+1 WHERE party_id=NEW.id AND status='pending'; UPDATE circle_provider_invitations SET status='closed',version=version+1 WHERE party_id=NEW.id AND status IN ('pending','accepted'); END",
    "CREATE TRIGGER circle_community_left AFTER UPDATE OF status ON memberships WHEN NEW.status='left' BEGIN UPDATE circle_member_invitations SET status='cancelled',version=version+1 WHERE invitee_id=NEW.user_id AND status IN ('pending','accepted') AND party_id IN (SELECT id FROM travel_parties WHERE community_id=NEW.community_id); DELETE FROM travel_party_members WHERE user_id=NEW.user_id AND party_id IN (SELECT p.id FROM travel_parties p JOIN circle_rooms r ON r.party_id=p.id WHERE p.community_id=NEW.community_id); UPDATE travel_parties SET status='closed' WHERE representative_id=NEW.user_id AND community_id=NEW.community_id AND id IN (SELECT party_id FROM circle_rooms); END",
)


def migrate(database):
    with database.transaction(True) as conn:
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version in (4, 5, 6, 7):
            return
        if version != 3:
            raise RuntimeError('Unsupported circles migration source')
        for statement in DDL:
            conn.execute(statement)
        conn.execute("INSERT INTO circle_rooms SELECT p.id,'legacy',MAX(2,(SELECT COUNT(*) FROM travel_party_members m WHERE m.party_id=p.id)),'[]',1,? FROM travel_parties p", (now(),))
        conn.execute('PRAGMA user_version=4')
