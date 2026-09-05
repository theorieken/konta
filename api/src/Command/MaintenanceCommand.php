<?php
declare(strict_types=1);
namespace App\Command;
use Cake\Command\Command;
use Cake\Console\{Arguments, ConsoleIo};
use App\Service\{Store, Delivery};
final class MaintenanceCommand extends Command
{
    public function execute(Arguments $args, ConsoleIo $io): ?int
    {
        $s = new Store(); $sent = (new Delivery($s))->flush(100);
        $s->db->execute('DELETE FROM tokens WHERE expires_at < ?', [time()]);
        $s->db->execute('DELETE FROM rate_limits WHERE expires_at < ?', [time()]);
        $s->db->execute('DELETE FROM records WHERE deleted_at IS NOT NULL AND deleted_at < ?', [time() - 90 * 86400]);
        $s->db->execute('DELETE FROM outbox WHERE sent_at IS NOT NULL AND sent_at < ?', [time() - 7 * 86400]);
        $io->out('Delivered: ' . $sent);
        return self::CODE_SUCCESS;
    }
}
