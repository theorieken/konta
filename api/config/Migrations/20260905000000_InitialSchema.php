<?php
declare(strict_types=1);
use Migrations\BaseMigration;
final class InitialSchema extends BaseMigration
{
    public function change(): void
    {
        $this->table('users', ['id' => false, 'primary_key' => ['id']])
            ->addColumn('id', 'string', ['limit' => 36])->addColumn('name', 'string', ['limit' => 100])
            ->addColumn('email', 'string', ['limit' => 254])->addColumn('password_hash', 'string', ['limit' => 255])
            ->addColumn('verified', 'boolean', ['default' => false])->addColumn('created_at', 'integer')
            ->addIndex(['email'], ['unique' => true])->create();
        $this->table('tokens', ['id' => false, 'primary_key' => ['hash']])
            ->addColumn('hash', 'string', ['limit' => 64])->addColumn('user_id', 'string', ['limit' => 36])
            ->addColumn('purpose', 'string', ['limit' => 16])->addColumn('expires_at', 'integer')
            ->addForeignKey('user_id', 'users', 'id', ['delete' => 'CASCADE'])->create();
        $this->table('households', ['id' => false, 'primary_key' => ['id']])
            ->addColumn('id', 'string', ['limit' => 36])->addColumn('name', 'string', ['limit' => 100])
            ->addColumn('settings', 'text')->addColumn('version', 'integer', ['default' => 1])->create();
        $this->table('memberships', ['id' => false, 'primary_key' => ['household_id', 'user_id']])
            ->addColumn('household_id', 'string', ['limit' => 36])->addColumn('user_id', 'string', ['limit' => 36])
            ->addColumn('role', 'string', ['limit' => 16])
            ->addForeignKey('household_id', 'households', 'id', ['delete' => 'CASCADE'])
            ->addForeignKey('user_id', 'users', 'id', ['delete' => 'CASCADE'])->create();
        $this->table('records', ['id' => false, 'primary_key' => ['id']])
            ->addColumn('id', 'string', ['limit' => 36])->addColumn('household_id', 'string', ['limit' => 36])
            ->addColumn('kind', 'string', ['limit' => 16])->addColumn('payload', 'text')
            ->addColumn('version', 'integer', ['default' => 1])->addColumn('created_by', 'string', ['limit' => 36, 'null' => true])
            ->addColumn('created_at', 'integer')->addColumn('updated_at', 'integer')->addColumn('deleted_at', 'integer', ['null' => true])
            ->addColumn('import_hash', 'string', ['limit' => 64, 'null' => true])
            ->addColumn('matched_plan_key', 'string', ['limit' => 100, 'null' => true])
            ->addIndex(['household_id', 'kind'])->addIndex(['household_id', 'import_hash'], ['unique' => true])
            ->addIndex(['household_id', 'matched_plan_key'], ['unique' => true])
            ->addForeignKey('household_id', 'households', 'id', ['delete' => 'CASCADE'])
            ->addForeignKey('created_by', 'users', 'id', ['delete' => 'SET_NULL'])->create();
        $this->table('invitations', ['id' => false, 'primary_key' => ['id']])
            ->addColumn('id', 'string', ['limit' => 36])->addColumn('household_id', 'string', ['limit' => 36])
            ->addColumn('email', 'string', ['limit' => 254])->addColumn('status', 'string', ['limit' => 16, 'default' => 'pending'])
            ->addColumn('expires_at', 'integer')->addColumn('created_at', 'integer')
            ->addForeignKey('household_id', 'households', 'id', ['delete' => 'CASCADE'])->create();
        $this->table('notifications', ['id' => false, 'primary_key' => ['id']])
            ->addColumn('id', 'string', ['limit' => 36])->addColumn('user_id', 'string', ['limit' => 36])
            ->addColumn('payload', 'text')->addColumn('is_read', 'boolean', ['default' => false])->addColumn('created_at', 'integer')
            ->addForeignKey('user_id', 'users', 'id', ['delete' => 'CASCADE'])->create();
        $this->table('devices', ['id' => false, 'primary_key' => ['token']])
            ->addColumn('token', 'string', ['limit' => 256])->addColumn('user_id', 'string', ['limit' => 36])
            ->addColumn('platform', 'string', ['limit' => 10])->addColumn('environment', 'string', ['limit' => 16])
            ->addForeignKey('user_id', 'users', 'id', ['delete' => 'CASCADE'])->create();
        $this->table('uploads', ['id' => false, 'primary_key' => ['id']])
            ->addColumn('id', 'string', ['limit' => 36])->addColumn('household_id', 'string', ['limit' => 36])
            ->addColumn('name', 'string', ['limit' => 255])->addColumn('status', 'string', ['limit' => 16])
            ->addColumn('imported', 'integer', ['default' => 0])->addColumn('duplicates', 'integer', ['default' => 0])
            ->addColumn('created_at', 'integer')->addForeignKey('household_id', 'households', 'id', ['delete' => 'CASCADE'])->create();
        $this->table('outbox', ['id' => false, 'primary_key' => ['id']])
            ->addColumn('id', 'string', ['limit' => 36])->addColumn('channel', 'string', ['limit' => 10])
            ->addColumn('recipient', 'string', ['limit' => 254])->addColumn('payload', 'text')
            ->addColumn('attempts', 'integer', ['default' => 0])->addColumn('available_at', 'integer')
            ->addColumn('locked_until', 'integer', ['default' => 0])->addColumn('sent_at', 'integer', ['null' => true])->create();
        $this->table('rate_limits', ['id' => false, 'primary_key' => ['id']])
            ->addColumn('id', 'string', ['limit' => 64])->addColumn('attempts', 'integer')->addColumn('expires_at', 'integer')->create();
    }
}
