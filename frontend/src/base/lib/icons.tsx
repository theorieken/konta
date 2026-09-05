'use client';

import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import BoltIcon from '@mui/icons-material/Bolt';
import CardGiftcardIcon from '@mui/icons-material/CardGiftcard';
import ChairIcon from '@mui/icons-material/Chair';
import CreditCardIcon from '@mui/icons-material/CreditCard';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import FavoriteIcon from '@mui/icons-material/Favorite';
import FlightIcon from '@mui/icons-material/Flight';
import HomeIcon from '@mui/icons-material/Home';
import LocalActivityIcon from '@mui/icons-material/LocalActivity';
import MedicalServicesIcon from '@mui/icons-material/MedicalServices';
import MoreHorizIcon from '@mui/icons-material/MoreHoriz';
import PaymentsIcon from '@mui/icons-material/Payments';
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong';
import RequestQuoteIcon from '@mui/icons-material/RequestQuote';
import SavingsIcon from '@mui/icons-material/Savings';
import SchoolIcon from '@mui/icons-material/School';
import ShieldIcon from '@mui/icons-material/Shield';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import SubscriptionsIcon from '@mui/icons-material/Subscriptions';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import UndoIcon from '@mui/icons-material/Undo';
import WorkIcon from '@mui/icons-material/Work';
import type { SvgIconProps } from '@mui/material/SvgIcon';
import type { ComponentType } from 'react';

/**
 * Categories store their icon as a snake_case name (see
 * backend/finance/services/seed.py). This map turns it into a component.
 */
const ICONS: Record<string, ComponentType<SvgIconProps>> = {
  account_balance: AccountBalanceIcon,
  bolt: BoltIcon,
  card_giftcard: CardGiftcardIcon,
  chair: ChairIcon,
  credit_card: CreditCardIcon,
  directions_car: DirectionsCarIcon,
  favorite: FavoriteIcon,
  flight: FlightIcon,
  home: HomeIcon,
  local_activity: LocalActivityIcon,
  medical_services: MedicalServicesIcon,
  more_horiz: MoreHorizIcon,
  payments: PaymentsIcon,
  receipt_long: ReceiptLongIcon,
  request_quote: RequestQuoteIcon,
  savings: SavingsIcon,
  school: SchoolIcon,
  shield: ShieldIcon,
  shopping_cart: ShoppingCartIcon,
  subscriptions: SubscriptionsIcon,
  swap_horiz: SwapHorizIcon,
  trending_up: TrendingUpIcon,
  undo: UndoIcon,
  wallet: AccountBalanceWalletIcon,
  work: WorkIcon,
};

export function CategoryIcon({ name, ...props }: { name?: string | null } & SvgIconProps) {
  const Icon = (name && ICONS[name]) || MoreHorizIcon;
  return <Icon {...props} />;
}

export function hasIcon(name?: string | null): boolean {
  return Boolean(name && ICONS[name]);
}

export const ICON_NAMES = Object.keys(ICONS);
